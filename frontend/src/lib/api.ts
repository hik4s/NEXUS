import type { Page } from './types';

const messages: Record<string, string> = {
  invalid_credentials: 'E-mail ou senha não conferem.',
  unauthorized: 'Sua sessão terminou. Entre novamente para continuar.',
  forbidden: 'Seu perfil não permite esta ação.',
  catalog_changed: 'Os preços do catálogo mudaram. Revalide a revisão antes de gerar os rascunhos.',
  invalid_selection: 'Revise a seleção: escolha somente pedidos válidos desta importação.',
  duplicate_external_order_id: 'Uma das referências já gerou um pedido. Atualize a revisão.',
  daily_batch_limit: 'O limite diário de importações foi atingido. Tente novamente amanhã.',
  retained_batch_limit: 'O limite de importações salvas foi atingido. Solicite a limpeza ao administrador.',
  registration_disabled: 'O cadastro está fechado. Use uma conta de demonstração provisionada.',
  file_too_large: 'O arquivo excede o limite de 1 MiB.',
  upload_body_too_large: 'O upload excede o limite permitido.',
  unavailable: 'O serviço está indisponível ou iniciando. Aguarde um momento e consulte novamente.',
};

export class ApiError extends Error {
  constructor(public status: number, public code: string, public uncertain = false) {
    super(messages[code] || (status === 409 ? 'Esta ação conflita com o estado atual. Atualize os dados antes de continuar.' : status === 422 ? 'Confira os campos e o formato do arquivo. Nenhuma ação foi concluída.' : status === 404 ? 'Este registro não está disponível nesta empresa.' : 'Não foi possível concluir a solicitação. Consulte o estado salvo antes de tentar outra ação.'));
    this.name = 'ApiError';
  }
}

export class ApiClient {
  private token: string | null = null;
  constructor(public base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1', private fetcher: typeof fetch = (...args) => fetch(...args), private onUnauthorized?: () => void) {}
  setToken(token: string | null) { this.token = token; }
  private async send(path: string, method = 'GET', body?: unknown): Promise<Response> {
    const headers = new Headers();
    const requestToken = this.token;
    if (requestToken) headers.set('Authorization', `Bearer ${requestToken}`);
    const multipart = body instanceof FormData;
    if (body !== undefined && !multipart) headers.set('Content-Type', 'application/json');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15_000);
    try {
      const response = await this.fetcher(`${this.base}${path}`, { method, headers,
        body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
        signal: controller.signal, cache: 'no-store', credentials: 'omit' });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const code = typeof data.detail === 'object' && data.detail?.code ? String(data.detail.code) : response.status === 401 ? (path === '/auth/login' ? 'invalid_credentials' : 'unauthorized') : response.status === 403 ? 'forbidden' : response.status === 413 ? 'file_too_large' : response.status >= 500 ? 'unavailable' : 'request_failed';
        if (response.status === 401 && requestToken && this.token === requestToken) { this.token = null; this.onUnauthorized?.(); }
        throw new ApiError(response.status, code, method !== 'GET' && response.status >= 500);
      }
      return response;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(0, 'unavailable', method !== 'GET');
    } finally { clearTimeout(timer); }
  }
  async get<T>(path: string): Promise<T> { return (await this.send(path)).json(); }
  async post<T>(path: string, body: unknown = {}): Promise<T> { return (await this.send(path, 'POST', body)).json(); }
  async patch<T>(path: string, body: unknown): Promise<T> { return (await this.send(path, 'PATCH', body)).json(); }
  async upload<T>(path: string, body: FormData): Promise<T> { return (await this.send(path, 'POST', body)).json(); }
  async page<T>(path: string, page = 1, pageSize = 12): Promise<Page<T>> {
    const response = await this.send(`${path}${path.includes('?') ? '&' : '?'}page=${page}&page_size=${pageSize}`);
    const items: T[] = await response.json();
    return { items, total: Number(response.headers.get('X-Total-Count') || items.length), page, pageSize };
  }
  async download(path: string, filename: string) {
    const blob = await (await this.send(path)).blob();
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
    anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
  }
}
