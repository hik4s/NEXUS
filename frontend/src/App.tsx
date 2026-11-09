import { useEffect, useRef, useState } from 'react';
import { ApiClient, ApiError } from './lib/api';
import type { Company, Login, User } from './lib/types';
import { canOperate } from './lib/types';
import { useResource } from './lib/hooks';
import { ErrorNotice, Icon, labels, Loading } from './components/ui';
import { LoginPage } from './features/auth/LoginPage';
import { OverviewPage } from './features/overview/OverviewPage';
import { ImportsPage } from './features/imports/ImportsPage';
import { ImportDetail } from './features/imports/ImportDetail';
import { OrdersPage } from './features/sales/OrdersPage';
import { OrderDetail } from './features/sales/OrderDetail';
import { CatalogPage } from './features/setup/CatalogPage';
import { InventoryPage } from './features/inventory/InventoryPage';
import { FinancePage } from './features/finance/FinancePage';
import { AuditPage } from './features/audit/AuditPage';

const links = [
  { path: 'overview', label: 'Visão geral', icon: 'overview', group: 'Workspace', private: false },
  { path: 'imports', label: 'Importações', icon: 'imports', group: 'Workspace', private: true },
  { path: 'orders', label: 'Pedidos', icon: 'orders', group: 'Workspace', private: true },
  { path: 'finance', label: 'Recebíveis', icon: 'finance', group: 'Workspace', private: true },
  { path: 'catalog', label: 'Catálogo', icon: 'catalog', group: 'Preparação', private: false },
  { path: 'inventory', label: 'Estoque', icon: 'inventory', group: 'Preparação', private: false },
  { path: 'audit', label: 'Auditoria', icon: 'audit', group: 'Controle', private: true },
];

export default function App() {
  const [user, setUser] = useState<User | null>(null); const [expired, setExpired] = useState(false);
  const [client] = useState(() => new ApiClient(undefined, undefined, () => { setUser(null); setExpired(true); window.location.hash = '/overview'; }));
  function login(login: Login) { client.setToken(login.access_token); setUser(login.user); setExpired(false); window.location.hash = '/overview'; }
  function logout() { client.setToken(null); setUser(null); setExpired(false); window.location.hash = '/overview'; }
  return user ? <Workspace key={user.id} client={client} user={user} logout={logout}/> : <LoginPage client={client} onLogin={login} expired={expired}/>;
}

function Workspace({ client, user, logout }: { client: ApiClient; user: User; logout: () => void }) {
  const [route, setRoute] = useState(() => window.location.hash.slice(2) || 'overview');
  const titleRef = useRef<HTMLElement>(null);
  useEffect(() => { const change = () => { setRoute(window.location.hash.slice(2) || 'overview'); window.scrollTo(0, 0); titleRef.current?.focus({ preventScroll: true }); }; window.addEventListener('hashchange', change); return () => window.removeEventListener('hashchange', change); }, []);
  const company = useResource(() => client.get<Company>('/companies/me'), [client, user.company_id]);
  const [page, id] = route.split('/'); const active = links.find(link => link.path === page); const operate = canOperate(user);
  const visibleLinks = links.filter(link => !link.private || operate);
  let content;
  if (!active) content = <div className="notice"><p>Esta página não está disponível.</p><a className="text-link" href="#/overview">Voltar à visão geral</a></div>;
  else if (active.private && !operate) content = <ErrorNotice error={new ApiError(403, 'forbidden')}/>;
  else if (page === 'imports') content = id ? <ImportDetail client={client} id={id}/> : <ImportsPage client={client}/>;
  else if (page === 'orders') content = id ? <OrderDetail client={client} id={id}/> : <OrdersPage client={client}/>;
  else if (page === 'catalog') content = <CatalogPage client={client} user={user}/>;
  else if (page === 'inventory') content = <InventoryPage client={client} user={user}/>;
  else if (page === 'finance') content = <FinancePage client={client}/>;
  else if (page === 'audit') content = <AuditPage client={client}/>;
  else content = <OverviewPage client={client} user={user}/>;
  return <div className="app-shell"><a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); titleRef.current?.focus({ preventScroll: true }); }}>Pular para o conteúdo</a><aside className="sidebar"><a className="sidebar-brand" href="#/overview" aria-label="NEXUS início"><img src="/brand/symbol.svg" alt=""/><span>NEXUS<small>OPERAÇÕES CONECTADAS</small></span></a><nav aria-label="Navegação principal"><div className="nav-groups">{['Workspace', 'Preparação', 'Controle'].map(group => <div className="nav-group" key={group}><span className="nav-label">{group}</span>{visibleLinks.filter(link => link.group === group).map(link => <a href={`#/${link.path}`} key={link.path} className={`nav-link ${page === link.path ? 'active' : ''}`} aria-current={page === link.path ? 'page' : undefined}><Icon name={link.icon} size={19}/><span>{link.label}</span>{page === link.path && <span className="nav-indicator"/>}</a>)}</div>)}</div></nav><div className="sidebar-bottom"><div className="sidebar-note"><Icon name="audit" size={19}/><span>Seu negócio,<br/><strong>cada etapa conectada.</strong></span></div><div className="version-line"><span className="live-dot"/>MVP de portfólio<span>NEXUS</span></div></div></aside>
    <div className="workspace-shell"><header className="workspace-header"><div className="breadcrumb"><span>Workspace</span><Icon name="chevron" size={13}/><strong>{active?.label || 'Página'}</strong></div><div className="header-right"><span className="workspace-chip"><span className="live-dot"/>{company.data?.name || 'Carregando empresa…'}</span><details className="user-menu"><summary aria-label="Menu da sessão"><span className="avatar">{user.full_name.split(' ').map(value => value[0]).slice(0, 2).join('')}</span><span className="user-name">{user.full_name}<small>{labels[user.role] || 'Usuário'}</small></span><span aria-hidden="true">⌄</span></summary><div className="user-dropdown"><strong>{user.full_name}</strong><small>{user.email}</small><button className="button subtle" onClick={logout}><Icon name="logout" size={16}/>Sair do workspace</button></div></details></div></header>
      <main id="main-content" tabIndex={-1} ref={titleRef} className="main-content">{company.loading ? <Loading/> : company.error ? <ErrorNotice error={company.error} onRetry={company.reload}/> : <div key={route} className="page-content">{content}</div>}<footer className="workspace-footer"><span>NEXUS · Gestão operacional conectada</span><span>Dados da empresa autorizada nesta sessão</span></footer></main>
    </div>
  </div>;
}
