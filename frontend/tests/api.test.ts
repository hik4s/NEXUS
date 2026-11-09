import { describe, it, expect, vi } from 'vitest';
import { ApiClient, ApiError } from '../src/lib/api';

describe('API e sessão', () => {
  it('trata 401 e encerra sessão sem expor resposta interna', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{"detail":"private-host"}', { status: 401 }));
    const expired = vi.fn();
    const api = new ApiClient('http://localhost/api/v1', fetcher, expired);
    api.setToken('dedicated-test-token');
    await expect(api.get('/auth/me')).rejects.toMatchObject({ status: 401, code: 'unauthorized' });
    expect(expired).toHaveBeenCalledOnce();
    expect(localStorage.getItem('nexus_token')).toBeNull();
  });
  it.each([[403, 'forbidden'], [409, 'catalog_changed'], [422, 'invalid_selection'], [503, 'unavailable']])(
    'interpreta %s com código estável', async (status, code) => {
      const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code, message: 'server-internal-message' } }), { status }));
      const api = new ApiClient('http://localhost', fetcher);
      try { await api.get('/resource'); throw Error('expected API failure'); }
      catch (error) { expect(error).toBeInstanceOf(ApiError); expect(error).toMatchObject({ status, code }); expect((error as Error).message).not.toContain('server-internal'); }
    });
  it('não repete mutação após erro de rede e sinaliza resultado desconhecido', async () => {
    const fetcher = vi.fn().mockRejectedValue(new TypeError('network unavailable'));
    const api = new ApiClient('http://localhost', fetcher);
    await expect(api.post('/orders', {})).rejects.toMatchObject({ status: 0, uncertain: true });
    expect(fetcher).toHaveBeenCalledOnce();
  });
  it('envia multipart sem Content-Type JSON e lê paginação', async () => {
    const fetcher = vi.fn().mockImplementation(async () => new Response('[]', { headers: { 'X-Total-Count': '21' } }));
    const api = new ApiClient('http://localhost', fetcher);
    const file = new FormData(); file.set('file', new File(['a'], 'orders.csv'));
    await api.upload('/order-imports', file);
    expect(new Headers(fetcher.mock.calls[0][1].headers).has('content-type')).toBe(false);
    expect((await api.page('/orders')).total).toBe(21);
  });
  it('uma resposta 401 antiga não encerra uma sessão nova', async () => {
    let resolve!: (response: Response) => void;
    const fetcher = vi.fn().mockImplementation(() => new Promise<Response>(done => { resolve = done; }));
    const expired = vi.fn(); const api = new ApiClient('http://localhost', fetcher, expired);
    api.setToken('old-session'); const pending = api.get('/auth/me');
    api.setToken('new-session'); resolve(new Response('{}', { status: 401 }));
    await expect(pending).rejects.toMatchObject({ status: 401 });
    expect(expired).not.toHaveBeenCalled();
  });
});
