import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { ReviewSelection } from '../src/features/imports/ReviewSelection';
import type { ImportEntry } from '../src/lib/types';

const entry = (id: string, status: ImportEntry['status']): ImportEntry => ({
  id, status, external_order_id: id, source_lines: [2], normalized_items: [{ sku: 'PROD-A', quantity: 1, row: 2, unit_price: '10.00' }],
  errors: status === 'invalid' ? [{ row: 2, field: 'sku', code: 'sku_not_found', message: 'SKU não encontrado.' }] : [], warnings: [], sales_order_id: null,
});
it('permite selecionar somente pedidos válidos e não submete duas vezes durante processamento', async () => {
  const user = userEvent.setup(); const commit = vi.fn();
  const { rerender } = render(<ReviewSelection entries={[entry('Válido', 'valid'), entry('Inválido', 'invalid')]} busy={false} onCommit={commit} />);
  expect(screen.getByRole('checkbox', { name: 'Selecionar Inválido' })).toBeDisabled();
  await user.click(screen.getByRole('checkbox', { name: 'Selecionar Válido' }));
  await user.click(screen.getByRole('button', { name: /Gerar 1 rascunho/ }));
  expect(commit).toHaveBeenCalledWith(['Válido']);
  rerender(<ReviewSelection entries={[entry('Válido', 'valid')]} busy onCommit={commit} />);
  expect(screen.getByRole('button', { name: /Gerando/ })).toBeDisabled();
});
