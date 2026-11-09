import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { ApiClient } from '../src/lib/api';
import { CatalogPage } from '../src/features/setup/CatalogPage';

it('uma criação incerta continua bloqueada durante recuperação e após GET malsucedido', async () => {
  let phase = 'initial'; const pending: ((response: Response) => void)[] = [];
  const fetcher = vi.fn().mockImplementation(async (_url: string, options: RequestInit) => {
    if (options.method === 'POST') throw new TypeError('connection lost');
    if (phase === 'pending') return new Promise<Response>(resolve => pending.push(resolve));
    return new Response('[]', { headers: { 'X-Total-Count': '0' } });
  });
  const user = userEvent.setup();
  render(<CatalogPage client={new ApiClient('http://localhost', fetcher)} user={{ id: 'u', company_id: 'c', full_name: 'Demo', email: 'demo@example.com', roles: ['admin'], role: 'admin' }}/>);
  await user.type(await screen.findByLabelText('Nome do cliente'), 'Cliente de demonstração');
  const submit = screen.getByRole('button', { name: 'Cadastrar cliente' });
  await user.click(submit); expect(await screen.findByRole('alert')).toHaveTextContent('ainda não foi confirmado');
  expect(submit).toBeDisabled();
  phase = 'pending'; await user.click(screen.getByRole('button', { name: 'Consultar estado salvo' }));
  await waitFor(() => expect(pending).toHaveLength(2)); expect(submit).toBeDisabled();
  for (const resolve of pending) resolve(new Response('{}', { status: 503 }));
  await waitFor(() => expect(screen.getAllByRole('alert').length).toBeGreaterThan(1));
  expect(submit).toBeDisabled();
  phase = 'ready'; await user.click(screen.getByRole('button', { name: 'Consultar estado salvo' }));
  await waitFor(() => expect(submit).toBeEnabled());
  expect(fetcher.mock.calls.filter(([, options]) => options.method === 'POST')).toHaveLength(1);
});
