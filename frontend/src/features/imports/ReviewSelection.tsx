import { useEffect, useState } from 'react';
import type { ImportEntry } from '../../lib/types';
import { Badge, Icon, money } from '../../components/ui';

export function ReviewSelection({ entries, busy, blocked = false, onCommit }: { entries: ImportEntry[]; busy: boolean; blocked?: boolean; onCommit: (ids: string[]) => void }) {
  const disabled = busy || blocked;
  const [selected, setSelected] = useState<string[]>([]);
  useEffect(() => setSelected([]), [entries]);
  const eligible = entries.filter(entry => entry.status === 'valid');
  const ids = selected.filter(id => eligible.some(entry => entry.id === id));
  function toggle(id: string) { setSelected(current => current.includes(id) ? current.filter(value => value !== id) : [...current, id]); }
  return <>
    <div className="table-wrap"><table><caption className="sr-only">Pedidos identificados no arquivo</caption><thead><tr>
      <th className="check-cell"><input type="checkbox" aria-label="Selecionar todos os pedidos válidos" disabled={disabled || !eligible.length} checked={!!eligible.length && ids.length === eligible.length} onChange={() => setSelected(ids.length === eligible.length ? [] : eligible.map(e => e.id))}/></th>
      <th>Referência / linhas</th><th>Itens e preço unitário</th><th>Revisão</th><th>Próximo passo</th>
    </tr></thead><tbody>{entries.map(entry => <tr key={entry.id} className={ids.includes(entry.id) ? 'selected-row' : ''}>
      <td><input type="checkbox" aria-label={`Selecionar ${entry.external_order_id}`} checked={ids.includes(entry.id)} disabled={disabled || entry.status !== 'valid'} onChange={() => toggle(entry.id)}/></td>
      <td><strong className="mono">{entry.external_order_id}</strong><small>Linhas {entry.source_lines.join(', ')}</small></td>
      <td>{entry.normalized_items.map((item, index) => <div className="item-line" key={`${item.sku}-${index}`}><span><strong>{item.quantity}×</strong> {item.sku}</span><small>{item.unit_price ? money(item.unit_price) : 'Sem preço no catálogo'}</small></div>)}</td>
      <td><Badge status={entry.status}/>{entry.errors.map((issue, index) => <p className="row-issue" key={index}>Linha {issue.row}: {issue.message}</p>)}{entry.warnings.map((issue, index) => <p className="row-warning" key={index}>{issue.message}</p>)}</td>
      <td>{entry.sales_order_id ? <a className="text-link" aria-label={`Abrir pedido ${entry.external_order_id}`} href={`#/orders/${entry.sales_order_id}`}>Abrir pedido <Icon name="arrow" size={15}/></a> : <span className="muted">{entry.status === 'valid' ? 'Gerar rascunho' : 'Corrigir e reenviar CSV'}</span>}</td>
    </tr>)}</tbody></table></div>
    <div className="selection-bar"><div><strong>{ids.length} de {eligible.length} pedido{eligible.length !== 1 && 's'} válido{eligible.length !== 1 && 's'} selecionado{ids.length !== 1 && 's'}</strong><small>Os rascunhos ainda não movimentam estoque nem financeiro.</small></div><button className="button primary" disabled={!ids.length || disabled} onClick={() => onCommit(ids)}>{busy ? 'Gerando…' : `Gerar ${ids.length} rascunho${ids.length !== 1 ? 's' : ''}`}<Icon name="arrow" size={17}/></button></div>
  </>;
}
