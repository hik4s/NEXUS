import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { ApiClient, ApiError } from '../src/lib/api';
import { ErrorNotice } from '../src/components/ui';
import { LoginPage } from '../src/features/auth/LoginPage';
import { ImportDetail } from '../src/features/imports/ImportDetail';

it.each([[401, 'unauthorized', /sessão terminou/], [403, 'forbidden', /perfil não permite/], [503, 'unavailable', /indisponível ou iniciando/]])('mostra orientação legível para erro %s', (status, code, message) => {
  const recover = vi.fn(); render(<ErrorNotice error={new ApiError(Number(status), String(code))} onRetry={recover}/>);
  expect(screen.getByRole('alert')).toHaveTextContent(message as RegExp);
  expect(screen.getByRole('button', { name: 'Tentar consulta novamente' })).toBeEnabled();
});

it('credenciais incorretas não são apresentadas como uma sessão expirada', async () => {
  const user = userEvent.setup(); const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 401 }));
  render(<LoginPage client={new ApiClient('http://localhost', fetcher)} onLogin={vi.fn()} expired={false}/>);
  await user.type(screen.getByLabelText('E-mail'), 'demo@example.com'); await user.type(screen.getByLabelText('Senha'), 'wrong-password');
  await user.click(screen.getByRole('button', { name: 'Entrar no workspace' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha não conferem.');
});

it('409 de catálogo exige clique explícito para revalidar e bloqueia outra geração', async () => {
  const user = userEvent.setup();
  const batch = { id: 'b1', filename: 'orders.csv', sha256: 'hash', status: 'reviewed', created_at: '2026-11-09T10:00:00Z', unassigned_errors: [], entries: [{ id: 'e1', external_order_id: 'DEMO', status: 'valid', source_lines: [2], normalized_items: [{ sku: 'PROD-A', quantity: 1, row: 2, unit_price: '10.00' }], errors: [], warnings: [], sales_order_id: null }] };
  const fetcher = vi.fn().mockImplementation(async (url: string) => url.endsWith('/commit') ? new Response(JSON.stringify({ detail: { code: 'catalog_changed' } }), { status: 409 }) : new Response(JSON.stringify(batch)));
  render(<ImportDetail client={new ApiClient('http://localhost', fetcher)} id="b1"/>);
  await user.click(await screen.findByRole('checkbox', { name: 'Selecionar DEMO' }));
  await user.click(screen.getByRole('button', { name: 'Gerar 1 rascunho' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Os preços do catálogo mudaram.');
  expect(fetcher.mock.calls.some(([url]) => String(url).endsWith('/revalidate'))).toBe(false);
  expect(screen.getByRole('button', { name: 'Gerar 1 rascunho' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Revalidar catálogo' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Catálogo revalidado');
  expect(fetcher.mock.calls.filter(([url]) => String(url).endsWith('/revalidate'))).toHaveLength(1);
});
