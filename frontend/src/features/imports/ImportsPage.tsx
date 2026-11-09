import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiClient, ApiError } from '../../lib/api';
import type { Batch, BatchSummary } from '../../lib/types';
import { useAction, useResource } from '../../lib/hooks';
import { Badge, dateTime, Empty, ErrorNotice, Icon, Loading, PageHeading, Pagination, Panel } from '../../components/ui';

export function ImportsPage({ client }: { client: ApiClient }) {
  const [page, setPage] = useState(1); const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<ApiError>(); const input = useRef<HTMLInputElement>(null);
  const action = useAction(); const resource = useResource(() => client.page<BatchSummary>('/order-imports', page), [client, page]);
  function choose(file?: File) { setFileError(undefined); setFile(file || null); if (file && file.size > 1048576) setFileError(new ApiError(413, 'file_too_large')); }
  function submit(event: FormEvent) { event.preventDefault(); if (!file || fileError) return; void action.run(async () => { const body = new FormData(); body.set('file', file); const batch = await client.upload<Batch>('/order-imports', body); window.location.hash = `/imports/${batch.id}`; }); }
  const recover = async () => { if (await resource.reload()) action.reset(); };
  return <>
    <PageHeading eyebrow="Pedidos, com contexto" title="Importações" description="Do arquivo à operação. Revise cada pedido antes de seguir."/>
    <div className="import-intro"><Panel title="Nova importação" aside={<span className="tiny-label">CSV · ATÉ 1 MiB</span>}>
      <form onSubmit={submit}><label className={`dropzone ${file ? 'has-file' : ''}`} htmlFor="order-file" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); choose(event.dataTransfer.files[0]); }}>
        <span className="upload-symbol"><Icon name="imports" size={28}/></span><strong>{file ? file.name : 'Traga seus próximos pedidos'}</strong><span>{file ? `${(file.size / 1024).toFixed(1)} KB · arquivo selecionado` : 'Arraste um CSV ou escolha um arquivo'}</span><span className="button secondary small">{file ? 'Trocar arquivo' : 'Escolher arquivo'}</span>
        <input className="sr-only" id="order-file" type="file" accept=".csv,text/csv" ref={input} onChange={event => choose(event.target.files?.[0])}/>
      </label><ErrorNotice error={fileError}/><div className="form-footer"><span>Somente os pedidos selecionados seguem para rascunho.</span><button className="button primary" disabled={!file || !!fileError || action.blocked}>{action.busy ? 'Revisando…' : 'Revisar arquivo'}<Icon name="arrow" size={17}/></button></div></form>
    </Panel><Panel className="guide-panel"><span className="eyebrow">Um arquivo simples</span><h2>Três colunas.<br/>Uma operação conectada.</h2><p>Os preços vêm do seu catálogo. Referências iguais agrupam os itens de um pedido.</p><div className="code-sample"><span>external_order_id,sku,quantity</span><span>DEMO-001,PROD-A,2</span><span>DEMO-001,PROD-B,1</span></div><ul className="check-list"><li><Icon name="check" size={15}/>Até 500 linhas e 100 pedidos</li><li><Icon name="check" size={15}/>Erros apresentados por pedido e linha</li><li><Icon name="check" size={15}/>O estoque só muda na confirmação</li></ul><a className="text-link" href="/demo/orders-valid.csv" download>Baixar modelo CSV <Icon name="arrow" size={15}/></a></Panel></div>
    <ErrorNotice error={action.error} onRetry={recover}/>
    <Panel title="Histórico de importações" aside={<button className="button subtle small" onClick={recover}><Icon name="refresh" size={15}/>Atualizar lista</button>}>
      {resource.loading ? <Loading/> : resource.error ? <ErrorNotice error={resource.error} onRetry={resource.reload}/> : !resource.data?.items.length ? <Empty title="Sua primeira importação começa aqui">Envie um arquivo para revisar os pedidos e gerar os rascunhos.</Empty> : <><div className="table-wrap"><table><thead><tr><th>Arquivo</th><th>Recebido em</th><th>Estado</th><th><span className="sr-only">Detalhe</span></th></tr></thead><tbody>{resource.data.items.map(batch => <tr key={batch.id}><td><a className="file-link" href={`#/imports/${batch.id}`}><Icon name="file"/><strong>{batch.filename}</strong></a></td><td>{dateTime(batch.created_at)}</td><td><Badge status={batch.status}/></td><td><a className="text-link" href={`#/imports/${batch.id}`}>Abrir revisão <Icon name="chevron" size={14}/></a></td></tr>)}</tbody></table></div><Pagination {...resource.data} onChange={setPage}/></>}
    </Panel>
  </>;
}
