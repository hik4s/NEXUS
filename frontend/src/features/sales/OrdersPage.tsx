import { useState } from 'react';
import { ApiClient } from '../../lib/api';
import type { Order } from '../../lib/types';
import { useResource } from '../../lib/hooks';
import { Badge, dateTime, Empty, ErrorNotice, Icon, Loading, money, PageHeading, Pagination, Panel } from '../../components/ui';

export function OrdersPage({ client }: { client: ApiClient }) {
  const [status, setStatus] = useState(''); const [page, setPage] = useState(1);
  const resource = useResource(() => client.page<Order>(`/sales/orders?${status ? `status_filter=${status}` : ''}`, page), [client, status, page]);
  return <><PageHeading title="Pedidos de venda" description="Acompanhe cada venda, do rascunho à confirmação."><a className="button primary" href="#/imports"><Icon name="plus" size={17}/>Importar pedidos</a></PageHeading><Panel title="Sua operação comercial" aside={<div className="inline-actions"><label className="sr-only" htmlFor="order-status">Filtrar pedidos</label><select id="order-status" value={status} onChange={event => { setStatus(event.target.value); setPage(1); }}><option value="">Todos os estados</option><option value="draft">Rascunhos</option><option value="confirmed">Confirmados</option><option value="cancelled">Cancelados</option></select><button className="button subtle icon-button" aria-label="Atualizar pedidos" onClick={resource.reload}><Icon name="refresh" size={17}/></button></div>}>
    {resource.loading ? <Loading/> : resource.error ? <ErrorNotice error={resource.error} onRetry={resource.reload}/> : !resource.data?.items.length ? <Empty title="Nenhum pedido nesta seleção">Importe um arquivo ou escolha outro estado para consultar.</Empty> : <><div className="table-wrap"><table><thead><tr><th>Pedido</th><th>Criado em</th><th>Itens</th><th>Estado</th><th className="numeric">Total</th><th><span className="sr-only">Detalhe</span></th></tr></thead><tbody>{resource.data.items.map(order => <tr key={order.id}><td><a className="mono strong text-link" href={`#/orders/${order.id}`}>{order.order_number}</a></td><td>{dateTime(order.created_at)}</td><td>{order.items.length} produto{order.items.length !== 1 && 's'}</td><td><Badge status={order.status}/></td><td className="numeric strong">{money(order.total)}</td><td><a className="text-link" aria-label={`Abrir ${order.order_number}`} href={`#/orders/${order.id}`}><Icon name="chevron" size={16}/></a></td></tr>)}</tbody></table></div><Pagination {...resource.data} onChange={setPage}/></>}
  </Panel></>;
}
