import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import type { ApiError } from '../lib/api';

export const money = (value: string | number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value));
export const dateTime = (value: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
export const dateOnly = (value: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(`${value}T12:00:00`));
export const labels: Record<string, string> = { draft: 'Rascunho', confirmed: 'Confirmado', cancelled: 'Cancelado', reviewed: 'Revisada', committed: 'Rascunhos gerados', partially_committed: 'Parcialmente gerada', valid: 'Pronto para gerar', invalid: 'Requer revisão', duplicate: 'Referência já usada', pending: 'Em aberto', paid: 'Recebido', partially_paid: 'Recebimento parcial', overdue: 'Em atraso', receipt: 'Entrada', issue: 'Saída', adjustment_in: 'Ajuste de entrada', adjustment_out: 'Ajuste de saída', sale: 'Venda', sale_return: 'Reversão da venda', admin: 'Administrador', manager: 'Gerente', employee: 'Operador' };
export function Badge({ status }: { status: string }) { return <span className={`badge badge-${status}`}><span aria-hidden="true" />{labels[status] || status}</span>; }
export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="11" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="18" width="7" height="3" rx="1"/></>,
    imports: <><path d="M12 3v11m-4-4 4 4 4-4M4 15v5h16v-5"/><path d="M4 4h3m10 0h3"/></>,
    orders: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z"/><path d="M9 7h6m-6 4h6m-6 4h3"/></>,
    catalog: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="M3 8v9l9 5 9-5V8M12 13v9M7.5 5.5l9 5"/></>,
    inventory: <><path d="m3 10 9-7 9 7v11H3V10Z"/><path d="M8 21V11h8v10m-8-5h8"/></>,
    finance: <><rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 9h18m-5 6h2M7 5V3"/></>,
    audit: <><path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3Z"/><path d="m8 12 3 3 5-6"/></>,
    arrow: <path d="M4 12h15m-5-5 5 5-5 5"/>, plus: <path d="M12 5v14M5 12h14"/>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 6a8 8 0 0 1 13 3M5 15a8 8 0 0 0 13 3"/></>,
    check: <path d="m5 12 4 4L19 6"/>, chevron: <path d="m9 5 7 7-7 7"/>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    logout: <><path d="M10 4H4v16h6m5-12 4 4-4 4M9 12h10"/></>,
    file: <><path d="M5 3h9l5 5v13H5V3Zm9 0v6h5M8 13h8m-8 4h5"/></>,
    alert: <><path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.55" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.file}</svg>;
}
export function PageHeading({ eyebrow, title, description, children }: { eyebrow?: string; title: string; description: string; children?: ReactNode }) { return <div className="page-heading"><div><span className="eyebrow">{eyebrow || 'Operação conectada'}</span><h1>{title}</h1><p>{description}</p></div><div className="heading-actions">{children}</div></div>; }
export function Panel({ title, aside, children, className = '' }: { title?: string; aside?: ReactNode; children: ReactNode; className?: string }) { return <section className={`panel ${className}`}>{title && <div className="panel-heading"><h2>{title}</h2>{aside}</div>}{children}</section>; }
export function ErrorNotice({ error, onRetry }: { error?: ApiError; onRetry?: () => void }) { if (!error) return null; return <div className="notice error" role="alert"><Icon name="alert"/><div><strong>{error.uncertain ? 'O resultado desta ação ainda não foi confirmado.' : 'Não foi possível continuar.'}</strong><p>{error.message}</p>{onRetry && <button className="button subtle" onClick={onRetry}>{error.uncertain ? 'Consultar estado salvo' : 'Tentar consulta novamente'}</button>}</div></div>; }
export function Loading() { return <div className="loading" role="status"><span className="spinner"/>Carregando dados…</div>; }
export function Empty({ title, children }: { title: string; children?: ReactNode }) { return <div className="empty"><div className="empty-icon"><Icon name="file" size={28}/></div><h3>{title}</h3>{children && <p>{children}</p>}</div>; }
export function Pagination({ page, total, pageSize, onChange }: { page: number; total: number; pageSize: number; onChange: (page: number) => void }) { const pages = Math.max(1, Math.ceil(total / pageSize)); return <div className="pagination"><span>{total} registro{total !== 1 && 's'} · página {page} de {pages}</span><div><button className="button subtle small" disabled={page <= 1} onClick={() => onChange(page - 1)}>Anterior</button><button className="button subtle small" disabled={page >= pages} onClick={() => onChange(page + 1)}>Próxima</button></div></div>; }
export function ConfirmDialog({ open, title, description, onCancel, onConfirm }: { open: boolean; title: string; description: string; onCancel: () => void; onConfirm: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (open && !dialog.current?.open) dialog.current?.showModal(); else if (!open && dialog.current?.open) dialog.current?.close(); }, [open]);
  return <dialog ref={dialog} className="confirm-dialog" aria-labelledby="confirm-title" onCancel={event => { event.preventDefault(); onCancel(); }}><span className="dialog-icon"><Icon name="audit" size={26}/></span><h2 id="confirm-title">{title}</h2><p>{description}</p><div className="inline-actions"><button className="button secondary" onClick={onCancel}>Voltar</button><button className="button primary" onClick={onConfirm}>Confirmar operação</button></div></dialog>;
}
