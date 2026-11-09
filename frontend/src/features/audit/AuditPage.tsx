import { useState } from 'react';
import { ApiClient } from '../../lib/api';
import type { Audit } from '../../lib/types';
import { useResource } from '../../lib/hooks';
import { dateTime, Empty, ErrorNotice, Icon, Loading, PageHeading, Panel, Pagination } from '../../components/ui';

const actions: Record<string, string> = { 'auth.login': 'Acesso ao workspace', 'auth.register': 'Empresa criada', 'user.created': 'Usuário cadastrado', 'user.updated': 'Usuário atualizado', 'product.created': 'Produto cadastrado', 'warehouse.created': 'Depósito criado', 'inventory.movement.created': 'Movimento de estoque', 'order_import.reviewed': 'Arquivo revisado', 'order_import.revalidated': 'Importação revalidada', 'order_import.committed': 'Rascunhos gerados', 'sales_order.created': 'Pedido criado', 'sales_order.status_changed': 'Estado do pedido atualizado', 'inventory.sales_order.fulfilled': 'Estoque baixado na venda', 'inventory.sales_order.fulfillment_reversed': 'Estoque devolvido no cancelamento', 'finance.receivable.created': 'Recebível gerado', 'finance.receivable.cancelled': 'Recebível cancelado', 'customer.created': 'Cliente cadastrado' };
export function AuditPage({ client }: { client: ApiClient }) {
  const [page, setPage] = useState(1);
  const resource = useResource(() => client.page<Audit>('/audit-logs', page, 25), [client, page]);
  return <><PageHeading title="Auditoria" description="Cada etapa importante deixa um registro na sua empresa."><button className="button secondary" onClick={resource.reload}><Icon name="refresh" size={16}/>Atualizar registros</button></PageHeading><Panel title="Histórico da operação" aside={<span className="tiny-label">REGISTROS DA EMPRESA</span>}>
    {resource.loading ? <Loading/> : resource.error ? <ErrorNotice error={resource.error} onRetry={resource.reload}/> : !resource.data?.items.length ? <Empty title="Nenhuma atividade registrada">As próximas ações realizadas no workspace aparecerão aqui.</Empty> : <><ol className="audit-list">{resource.data.items.map(row => <li key={row.id}><span className={`audit-icon ${row.status === 'failure' ? 'failed' : ''}`}><Icon name={row.action.includes('inventory') ? 'inventory' : row.action.includes('finance') ? 'finance' : row.action.includes('order') ? 'orders' : 'audit'} size={18}/></span><div><strong>{actions[row.action] || 'Registro da operação'}</strong><small>{row.status === 'failure' ? 'Tentativa não concluída' : 'Ação registrada'} · {row.action}</small></div><time dateTime={row.created_at}>{dateTime(row.created_at)}</time></li>)}</ol><Pagination {...resource.data} onChange={setPage}/></>}
  </Panel></>;
}
