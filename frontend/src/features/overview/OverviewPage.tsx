import { ApiClient } from '../../lib/api';
import type { BatchSummary, FinanceSummary, Order, Product, Stock, User } from '../../lib/types';
import { canOperate } from '../../lib/types';
import { useResource } from '../../lib/hooks';
import { Badge, dateTime, Empty, ErrorNotice, Icon, Loading, money, PageHeading, Panel } from '../../components/ui';

export function OverviewPage({ client, user }: { client: ApiClient; user: User }) {
  const operate = canOperate(user);
  const resource = useResource(async () => {
    const [products, stock, orders, drafts, batches, finance] = await Promise.all([
      client.page<Product>(`/companies/${user.company_id}/products`, 1, 1), client.get<Stock[]>('/inventory/stock'),
      operate ? client.page<Order>('/sales/orders', 1, 4) : Promise.resolve(null),
      operate ? client.page<Order>('/sales/orders?status_filter=draft', 1, 1) : Promise.resolve(null),
      operate ? client.page<BatchSummary>('/order-imports', 1, 4) : Promise.resolve(null),
      operate ? client.get<FinanceSummary>('/finance/summary') : Promise.resolve(null),
    ]); return { products, stock, orders, drafts, batches, finance };
  }, [client, user.id]);
  const data = resource.data;
  return <><PageHeading eyebrow="Seu negócio em movimento" title="Visão geral" description="Uma visão clara do que está pronto e do que precisa seguir."><button className="button secondary" onClick={resource.reload}><Icon name="refresh" size={16}/>Atualizar dados</button></PageHeading>
    <section className="overview-hero"><div><span className="hero-kicker"><span className="live-dot"/>OPERAÇÃO CONECTADA</span><h2>Do pedido ao recebível.<br/>Cada etapa conectada.</h2><p>Importe, revise e confirme. Estoque e recebíveis<br className="desktop-only"/> acompanham cada venda no mesmo fluxo.</p><div className="inline-actions">{operate && <a className="button primary" href="#/imports"><Icon name="plus" size={17}/>Nova importação</a>}<a className="button ghost" href="#/catalog">Preparar catálogo <Icon name="arrow" size={16}/></a></div></div><div className="hero-graphic" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><img src="/brand/symbol.svg" alt=""/><span className="orbit-label label-one"><Icon name="file" size={15}/>Pedido</span><span className="orbit-label label-two"><Icon name="inventory" size={15}/>Estoque</span><span className="orbit-label label-three"><Icon name="finance" size={15}/>Recebível</span></div></section>
    {resource.loading ? <Loading/> : resource.error ? <ErrorNotice error={resource.error} onRetry={resource.reload}/> : data && <>
      <div className="stat-row overview-stats"><a href="#/catalog"><span><Icon name="catalog" size={17}/>Produtos no catálogo</span><strong>{data.products.total.toString().padStart(2, '0')}</strong><small>Prontos para os próximos pedidos <Icon name="arrow" size={14}/></small></a>{operate ? <><a href="#/orders"><span><Icon name="orders" size={17}/>Pedidos em rascunho</span><strong>{String(data.drafts?.total || 0).padStart(2, '0')}</strong><small>Aguardando confirmação <Icon name="arrow" size={14}/></small></a><a href="#/finance"><span><Icon name="finance" size={17}/>A receber em aberto</span><strong>{money(data.finance?.accounts_receivable_open || '0')}</strong><small>Consolidado pelo financeiro <Icon name="arrow" size={14}/></small></a></> : <a href="#/inventory"><span><Icon name="inventory" size={17}/>Saldos disponíveis</span><strong>{data.stock.length}</strong><small>Produtos e depósitos nesta empresa <Icon name="arrow" size={14}/></small></a>}</div>
      {operate && <div className="overview-grid"><Panel title="Pedidos recentes" aside={<a className="text-link" href="#/orders">Ver todos <Icon name="arrow" size={14}/></a>}>{!data.orders?.items.length ? <Empty title="Sua operação começa pelo primeiro pedido">Envie um CSV para preparar os rascunhos.</Empty> : <div className="table-wrap"><table><thead><tr><th>Pedido</th><th>Estado</th><th className="numeric">Total</th></tr></thead><tbody>{data.orders.items.map(order => <tr key={order.id}><td><a className="text-link mono" href={`#/orders/${order.id}`}>{order.order_number}</a><small>{dateTime(order.created_at)}</small></td><td><Badge status={order.status}/></td><td className="numeric strong">{money(order.total)}</td></tr>)}</tbody></table></div>}</Panel><Panel title="Últimas importações" aside={<a className="text-link" href="#/imports"><Icon name="arrow" size={16}/><span className="sr-only">Ver importações</span></a>}>{!data.batches?.items.length ? <Empty title="Nenhum arquivo recebido">As revisões ficam salvas aqui para você continuar depois.</Empty> : <div className="recent-files">{data.batches.items.map(batch => <a key={batch.id} href={`#/imports/${batch.id}`}><span className="file-avatar"><Icon name="file" size={20}/></span><div><strong>{batch.filename}</strong><small>{dateTime(batch.created_at)}</small><Badge status={batch.status}/></div><Icon name="chevron" size={15}/></a>)}</div>}</Panel></div>}
      <section className="next-step"><span className="next-icon"><Icon name="audit" size={22}/></span><div><h3>Antes de confirmar, confira.</h3><p>Preços vêm do catálogo. Saldo e recebível são validados pela operação de venda.</p></div><a className="text-link" href="#/inventory">Conferir estoque <Icon name="arrow" size={16}/></a></section>
    </>}
  </>;
}
