import { useEffect, useMemo, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

async function api(path, options = {}, token = localStorage.getItem('nexus_token')) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'API request failed');
  return data;
}

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({
    company_name: 'NovaTech Demo',
    company_slug: 'novatech-demo',
    full_name: 'NEXUS Admin',
    email: 'admin@example.com',
    password: 'StrongPass123!',
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';
      const payload = mode === 'login'
        ? { email: form.email, password: form.password }
        : form;
      const data = await api(endpoint, { method: 'POST', body: JSON.stringify(payload) }, null);
      localStorage.setItem('nexus_token', data.access_token);
      onAuthenticated(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <span className="eyebrow">NEXUS / IDENTITY</span>
        <h1>{mode === 'login' ? 'Entrar no NEXUS' : 'Criar seu workspace'}</h1>
        <p className="lead">Primeiro construímos identidade. Depois todo o resto do sistema passa por ela.</p>
        <form onSubmit={submit} className="form">
          {mode === 'register' && <>
            <input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} placeholder="Nome da empresa" required />
            <input value={form.company_slug} onChange={(e) => setForm({ ...form, company_slug: e.target.value })} placeholder="slug-da-empresa" required />
            <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Seu nome" required />
          </>}
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="E-mail" required />
          <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Senha" minLength="8" required />
          <button type="submit" disabled={busy}>{busy ? 'Processando...' : mode === 'login' ? 'Entrar' : 'Criar workspace'}</button>
        </form>
        {error && <div className="notice error">{error}</div>}
        <button className="secondary-button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>
          {mode === 'login' ? 'Ainda não tenho uma conta' : 'Já tenho uma conta'}
        </button>
      </section>
    </main>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('checking');
  const [company, setCompany] = useState(null);
  const [products, setProducts] = useState([]);
  const [product, setProduct] = useState({ name: '', sku: '', price: '', cost: '' });
  const [message, setMessage] = useState('');

  async function bootstrap() {
    try {
      const me = await api('/auth/me');
      setUser(me);
      setStatus('online');
      const currentCompany = await api('/companies/me');
      setCompany(currentCompany);
      const catalog = await api(`/companies/${currentCompany.id}/products`);
      setProducts(catalog);
    } catch (error) {
      localStorage.removeItem('nexus_token');
      setUser(null);
      setCompany(null);
      setProducts([]);
      setStatus(error.message?.includes('API') ? 'offline' : 'checking');
    }
  }

  useEffect(() => { bootstrap(); }, []);

  const totalCatalogValue = useMemo(
    () => products.reduce((sum, item) => sum + Number(item.price || 0), 0),
    [products],
  );

  async function handleCreateProduct(event) {
    event.preventDefault();
    if (!company) return;
    try {
      const created = await api(`/companies/${company.id}/products`, {
        method: 'POST',
        body: JSON.stringify({
          name: product.name,
          sku: product.sku,
          price: Number(product.price || 0),
          cost: Number(product.cost || 0),
        }),
      });
      setProducts((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setProduct({ name: '', sku: '', price: '', cost: '' });
      setMessage('Produto cadastrado.');
    } catch (error) {
      setMessage(error.message);
    }
  }

  function logout() {
    localStorage.removeItem('nexus_token');
    setUser(null);
    setCompany(null);
    setProducts([]);
  }

  if (!user) return <AuthScreen onAuthenticated={(nextUser) => { setUser(nextUser); bootstrap(); }} />;

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">NEXUS / 0.3.0</span>
          <h1>Business, connected.</h1>
          <p className="lead">Identity foundation ativa. Empresa, usuário, catálogo e API agora estão protegidos por autenticação.</p>
        </div>
        <div className="top-actions">
          <div className="status-card"><span className={`status-dot ${status}`} /><strong>API {status}</strong><span>{user.email}</span></div>
          <button className="secondary-button" onClick={logout}>Sair</button>
        </div>
      </header>

      <section className="metrics">
        <article><span>Empresa</span><strong>{company?.name || '—'}</strong></article>
        <article><span>Produtos</span><strong>{products.length}</strong></article>
        <article><span>Valor do catálogo</span><strong>R$ {totalCatalogValue.toFixed(2)}</strong></article>
      </section>

      <section className="workspace">
        <article className="panel">
          <div className="panel-heading"><h2>Identity</h2><span>{user.role.toUpperCase()}</span></div>
          <p className="muted"><strong>{user.full_name}</strong><br />{user.email}<br />Empresa: {company?.name}</p>
        </article>

        <article className="panel">
          <div className="panel-heading"><h2>Novo produto</h2><span>Sales / Inventory seed</span></div>
          <form onSubmit={handleCreateProduct} className="form grid-form">
            <input value={product.name} onChange={(e) => setProduct({ ...product, name: e.target.value })} placeholder="Produto" required />
            <input value={product.sku} onChange={(e) => setProduct({ ...product, sku: e.target.value })} placeholder="SKU" required />
            <input type="number" min="0" step="0.01" value={product.price} onChange={(e) => setProduct({ ...product, price: e.target.value })} placeholder="Preço" />
            <input type="number" min="0" step="0.01" value={product.cost} onChange={(e) => setProduct({ ...product, cost: e.target.value })} placeholder="Custo" />
            <button type="submit">Cadastrar produto</button>
          </form>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading"><h2>Produtos</h2><span>{company?.name || 'Nenhuma empresa'}</span></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Produto</th><th>SKU</th><th>Preço</th><th>Custo</th><th>Margem</th></tr></thead>
            <tbody>
              {products.map((item) => {
                const margin = Number(item.price) ? ((Number(item.price) - Number(item.cost)) / Number(item.price)) * 100 : 0;
                return <tr key={item.id}><td>{item.name}</td><td>{item.sku}</td><td>R$ {Number(item.price).toFixed(2)}</td><td>R$ {Number(item.cost).toFixed(2)}</td><td>{margin.toFixed(1)}%</td></tr>;
              })}
              {!products.length && <tr><td colSpan="5" className="empty">Nenhum produto cadastrado.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="intelligence-preview">
        <span className="eyebrow">NEXT / RBAC + BUSINESS DOMAINS</span>
        <h2>Identity está pronta para sustentar o restante do NEXUS.</h2>
        <p>O próximo bloco será RBAC, usuários internos e permissões por domínio. Depois entram CRM, vendas, estoque e financeiro sobre a mesma identidade.</p>
        {message && <div className="notice">{message}</div>}
      </section>
    </main>
  );
}
