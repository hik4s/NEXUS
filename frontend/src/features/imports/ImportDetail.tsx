import { useState } from 'react';
import { ApiClient } from '../../lib/api';
import type { Batch, CommitResult } from '../../lib/types';
import { useAction, useResource } from '../../lib/hooks';
import { Badge, dateTime, Empty, ErrorNotice, Icon, Loading, PageHeading, Panel } from '../../components/ui';
import { ReviewSelection } from './ReviewSelection';

export function ImportDetail({ client, id }: { client: ApiClient; id: string }) {
  const resource = useResource(() => client.get<Batch>(`/order-imports/${id}`), [client, id]);
  const action = useAction(); const [notice, setNotice] = useState('');
  async function refresh() { if (await resource.reload()) action.reset(); }
  if (resource.loading) return <Loading/>;
  if (resource.error) return <ErrorNotice error={resource.error} onRetry={refresh}/>;
  const batch = resource.data!; const valid = batch.entries.filter(entry => entry.status === 'valid').length;
  const invalid = batch.entries.filter(entry => entry.status === 'invalid' || entry.status === 'duplicate').length;
  return <>
    <a className="back-link" href="#/imports">← Todas as importações</a>
    <PageHeading eyebrow="Revisão de pedidos" title={batch.filename} description={`Recebido em ${dateTime(batch.created_at)} · confira os itens antes de gerar.`}><Badge status={batch.status}/><button className="button secondary" onClick={refresh}><Icon name="refresh" size={16}/>Atualizar revisão</button></PageHeading>
    <div className="workflow-strip"><span className="complete"><b>01</b> Arquivo recebido<Icon name="check" size={16}/></span><span className={batch.status === 'reviewed' ? 'current' : 'complete'}><b>02</b> Revisão dos pedidos</span><span className={batch.status !== 'reviewed' ? 'current' : ''}><b>03</b> Gerar rascunhos</span></div>
    <div className="stat-row compact"><div><span>Pedidos no arquivo</span><strong>{batch.entries.length}</strong></div><div><span>Prontos para gerar</span><strong className="success-text">{valid}</strong></div><div><span>Requerem atenção</span><strong className={invalid ? 'warning-text' : ''}>{invalid}</strong></div></div>
    <ErrorNotice error={action.error} onRetry={refresh}/>
    {action.error?.code === 'catalog_changed' && <div className="notice warning"><div><strong>Revalidação necessária</strong><p>Consulte os novos preços e revise a seleção novamente.</p></div><button className="button secondary" disabled={action.busy} onClick={() => void action.run(async () => { await client.post(`/order-imports/${id}/revalidate`); setNotice('Catálogo revalidado. Confira os preços antes de selecionar novamente.'); resource.reload(); })}>Revalidar catálogo</button></div>}
    {notice && <div className="notice success" role="status"><Icon name="check"/>{notice}</div>}
    {batch.unassigned_errors.length > 0 && <div className="notice warning"><Icon name="alert"/><div><strong>Linhas sem pedido associado</strong>{batch.unassigned_errors.map((issue, index) => <p key={index}>Linha {issue.row}: {issue.message}</p>)}</div></div>}
    <Panel title="Pedidos identificados" aside={<div className="inline-actions"><button className="button subtle small" disabled={action.blocked} onClick={() => void action.run(async () => { await client.post(`/order-imports/${id}/revalidate`); setNotice('Revisão atualizada com o catálogo atual.'); resource.reload(); })}>Revalidar dados</button><button className="button subtle small" disabled={action.blocked} onClick={() => void action.run(() => client.download(`/order-imports/${id}/errors.csv`, 'erros-importacao.csv'))}>Exportar erros</button></div>}>
      {batch.entries.length ? <ReviewSelection entries={batch.entries} busy={action.busy} blocked={!!action.error?.uncertain || action.error?.code === 'catalog_changed'} onCommit={ids => void action.run(async () => { const result = await client.post<CommitResult>(`/order-imports/${id}/commit`, { entry_ids: ids }); setNotice(`${result.orders.length} ${result.orders.length === 1 ? 'rascunho disponível' : 'rascunhos disponíveis'}. Abra o pedido para confirmar a venda.`); resource.reload(); })}/> : <Empty title="Nenhum pedido associável">Corrija as referências no arquivo e envie uma nova versão.</Empty>}
    </Panel>
  </>;
}
