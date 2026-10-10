# NEXUS — Frontend Roadmap

**Versão:** 1.0  
**Trilha:** Frontend  
**Objetivo final:** construir uma aplicação React empresarial, modular, responsiva, acessível, observável e pronta para consumir toda a plataforma NEXUS.

---

## 1. Princípios da trilha

1. O frontend não conterá regra de negócio crítica que deveria pertencer ao backend.
2. Componentes visuais devem ser reutilizáveis antes de cada módulo começar a criar soluções próprias.
3. O frontend deve tratar a API como contrato: tipos, estados de loading, erro, vazio e sucesso precisam ser explícitos.
4. Não criar telas de módulos avançados antes de existir o contrato mínimo da API.
5. A experiência final deve continuar funcional com grande volume de dados.
6. Toda funcionalidade importante deve terminar com teste ou critério manual de aceitação definido.

## 2. Arquitetura-alvo

```text
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── router/
│   │   ├── providers/
│   │   └── config/
│   ├── assets/
│   ├── components/
│   │   ├── ui/
│   │   ├── forms/
│   │   ├── data-display/
│   │   └── feedback/
│   ├── features/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── crm/
│   │   ├── sales/
│   │   ├── inventory/
│   │   ├── procurement/
│   │   ├── finance/
│   │   ├── logistics/
│   │   ├── workflow/
│   │   ├── automation/
│   │   └── intelligence/
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   ├── stores/
│   ├── styles/
│   └── main.jsx
├── tests/
└── package.json
```

A divisão por `features/` evita um frontend gigante onde páginas e componentes de todos os domínios ficam misturados.

---

# 3. Microtarefas

## FASE F0 — Fundação

### F-001 — Garantir execução local
- Confirmar Node/npm.
- Confirmar Vite.
- Criar comando único de desenvolvimento.

**Pronto quando:** `npm run dev` sobe sem erros.

### F-002 — Organizar estrutura por domínio
- Criar `app`, `components`, `features`, `services`, `stores` e `lib`.
- Mover arquivos sem alterar comportamento.

**Pronto quando:** o app continua executando após a reorganização.

### F-003 — Configuração por ambiente
- Criar acesso a `VITE_API_URL`.
- Separar configuração de desenvolvimento e produção.
- Nunca hardcodar segredo no frontend.

### F-004 — Sistema visual base
- Definir tipografia, espaçamento, bordas, sombras e tokens.
- Criar componentes base: Button, Input, Select, Modal, Badge, Card, Table, Spinner, Alert.

### F-005 — Layout do produto
- Sidebar.
- Header.
- Breadcrumb.
- Área de conteúdo.
- Responsividade.

**Marco F0:** shell visual completo e reutilizável.

---

## FASE F1 — Comunicação com a API

### F-006 — Cliente HTTP
- Centralizar `fetch` ou cliente escolhido.
- Base URL.
- Headers.
- Tratamento de erros.

### F-007 — Tipos/contratos da API
- Modelar respostas e payloads principais.
- Evitar objetos anônimos espalhados.

### F-008 — Estados de dados
Cada tela que consulta API deve ter:
- loading;
- sucesso;
- vazio;
- erro;
- retry quando aplicável.

### F-009 — Autorização automática
- Anexar token.
- Tratar 401.
- Redirecionar para login quando necessário.

**Marco F1:** frontend consegue consumir o backend de forma consistente.

---

## FASE F2 — Identity

### F-010 — Cadastro/login
- Tela de login.
- Cadastro inicial da empresa.
- Validação client-side.

### F-011 — Sessão
- Persistência controlada da sessão.
- Logout.
- Estado de usuário atual.

### F-012 — Proteção de rotas
- Rotas públicas.
- Rotas autenticadas.
- Fallback de permissão.

### F-013 — Contexto da empresa
- Exibir empresa ativa.
- Preparar suporte futuro a múltiplas empresas/unidades.

### F-014 — Permissões visuais
- Ocultar/disable ações sem permissão.
- Nunca tratar isso como segurança: a API continua sendo a autoridade.

**Marco F2:** usuário entra no NEXUS e vê somente o que seu perfil pode acessar.

---

## FASE F3 — Dashboard e plataforma

### F-015 — Dashboard base
- KPIs.
- Alertas.
- Atalhos.
- Atividade recente.

### F-016 — Componentes de dados
- Tabela paginada.
- Ordenação.
- Filtros.
- Busca.
- Exportação quando houver endpoint correspondente.

### F-017 — Gráficos
- Receita.
- Margem.
- Estoque.
- Fluxo de caixa.
- Tendências.

### F-018 — Notificações
- Centro de notificações.
- Toasts.
- Estados lidos/não lidos.

---

## FASE F4 — Domínios empresariais

Implementar cada domínio **um de cada vez**. Ordem sugerida:

### F-019 — CRM
- Clientes.
- Leads.
- Interações.
- Segmentos.

### F-020 — Sales
- Produtos.
- Pedidos.
- Itens.
- Descontos.
- Comissões.

### F-021 — Inventory
- Armazéns.
- Saldo.
- Movimentações.
- Transferências.
- Estoque mínimo.

### F-022 — Procurement
- Fornecedores.
- Pedidos de compra.
- Histórico de preços.

### F-023 — Finance
- Contas.
- A pagar.
- A receber.
- Transações.
- Fluxo de caixa.

### F-024 — Logistics
- Entregas.
- Motoristas.
- Veículos.
- Rotas.
- Rastreamento.

### F-025 — Workflow
- Tarefas.
- Aprovações.
- SLA.
- Escalonamentos.
- Comentários.

**Regra:** cada módulo precisa de listagem + criação/edição + detalhe + filtros + estados de erro/vazio antes de ser considerado concluído.

---

## FASE F5 — Intelligence UX

### F-026 — Intelligence Center
- Resumo das descobertas.
- Severidade.
- Evidências.
- Data/hora.

### F-027 — Alertas inteligentes
- Filtragem por severidade.
- Filtros por domínio.
- Ações sugeridas.

### F-028 — Chat com NEXUS AI
- Histórico de conversa.
- Streaming quando suportado.
- Indicação de fontes/dados usados.
- Estado de ferramenta em execução.

### F-029 — Aprovação de ações
- Exibir ação proposta.
- Mostrar impacto.
- Confirmar antes de executar.
- Exibir resultado da ação.

### F-030 — Explainability UI
- “Por que este alerta apareceu?”
- Evidências.
- Cálculos resumidos.
- Dados consultados.

---

## FASE F6 — Qualidade e produção

### F-031 — Testes unitários de componentes
- Componentes críticos.
- Formulários.
- Regras de apresentação.

### F-032 — Testes de integração
- Login.
- Fluxos principais de cada domínio.

### F-033 — E2E
- Login.
- Cadastro.
- Criação de venda.
- Alteração de estoque.
- Consulta financeira.
- Interação com NEXUS AI.

### F-034 — Acessibilidade
- Navegação por teclado.
- Labels.
- Contraste.
- Estados de foco.

### F-035 — Performance
- Lazy loading.
- Paginação real.
- Virtualização em tabelas grandes quando necessária.
- Evitar chamadas duplicadas.

### F-036 — Build e deploy
- Build de produção.
- Variáveis de ambiente.
- Deploy.
- Observabilidade de erros.

---

# 4. Dependências externas

O frontend depende de contratos do backend principalmente para:
- autenticação;
- permissões;
- paginação;
- filtros;
- erros;
- endpoints de inteligência.

A IA não deve ser integrada diretamente a partir do navegador por chave secreta. O navegador conversa com o backend, e o backend controla o provedor/modelo.

# 5. Critério de conclusão do Frontend

O frontend estará “pronto para a versão final” quando:

- todos os domínios principais possuírem telas funcionais;
- navegação e permissões forem consistentes;
- estados de loading/erro/vazio existirem nas telas importantes;
- testes E2E cobrirem os fluxos críticos;
- o Intelligence Center consumir a camada de IA sem expor credenciais;
- o layout suportar desktop e telas menores;
- o build de produção for reproduzível.
