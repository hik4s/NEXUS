# NEXUS — Master Plan

> **Documento mestre do produto, arquitetura, identidade visual e execução**  
> Versão: 1.0 · Atualizado em: 10 de outubro de 2026  
> Baseline recuperado: `v0.18.0 — B9 Cloud` · checkpoint local `e46cdcb`  
> Status: plano consolidado para retomada; estados técnicos precisam ser reconfirmados por execução dos testes.

---

## 1. Resumo executivo

O **NEXUS** é uma plataforma integrada de gestão empresarial, automação operacional e inteligência para pequenas e médias empresas (PMEs). A ambição é centralizar processos e informações, reduzir trabalho manual, oferecer indicadores confiáveis e transformar sinais do negócio em decisões e ações verificáveis.

O NEXUS não deve ser somente um conjunto de telas CRUD nem um chatbot sobreposto a um ERP. O valor do produto está na integração entre módulos transacionais, automações, dados confiáveis, explicabilidade, IA controlada e fluxos de trabalho auditáveis.

A plataforma está sendo construída como um **monólito modular**, com limites claros entre domínios. A separação em microsserviços só deve ocorrer quando houver uma necessidade comprovada de escala, isolamento de falhas ou implantação independente.

### Resultado pretendido

Uma empresa deve conseguir usar o NEXUS para entender o estado das operações, descobrir problemas, executar tarefas recorrentes, coordenar trabalho e consultar uma camada de inteligência que responda com base em dados autorizados — sem entregar à IA controle irrestrito sobre os dados ou as operações.

## 2. Visão, missão e objetivos

### Visão

Ser um centro operacional inteligente para PMEs: uma única plataforma para coordenar dados, processos, pessoas, automações e decisões empresariais.

### Missão

Tornar a gestão diária mais clara, rastreável e eficiente por meio de fluxos operacionais integrados, indicadores confiáveis e automação segura.

### Objetivos estratégicos

1. **Centralizar operações:** integrar CRM, vendas, estoque, compras, finanças, logística e workflows em uma experiência coerente.
2. **Reduzir trabalho manual:** automatizar tarefas repetitivas, importações, integrações e interações com sistemas legados.
3. **Melhorar a tomada de decisão:** converter registros operacionais em métricas, alertas, análises e recomendações rastreáveis.
4. **Adicionar IA útil, não decorativa:** permitir consultas e ações contextualizadas por ferramentas explicitamente autorizadas.
5. **Preservar controle e confiança:** aplicar isolamento entre empresas, permissões, logs de auditoria, aprovações e limites de execução.
6. **Construir uma base sustentável:** manter código modular, contratos explícitos, testes automatizados, migrações reversíveis e implantação reproduzível.
7. **Entregar incrementalmente:** dividir objetivos amplos em microtarefas demonstráveis, validadas antes de serem marcadas como concluídas.

### Como medir sucesso

As métricas de produto devem ser definidas com empresas-piloto. A lista inicial a instrumentar inclui tempo de conclusão das tarefas frequentes, redução de entrada manual, taxa de sucesso das automações, erros de importação, precisão e utilidade dos alertas, adoção dos módulos, latência da API, confiabilidade dos jobs e custo/latência das chamadas de IA. Não se devem inventar metas numéricas antes de existir baseline medido.

## 3. Problemas e usuários-alvo

### Problemas que o NEXUS pretende resolver

- Informações espalhadas entre planilhas e sistemas diferentes.
- Falta de visão consolidada de vendas, margem, estoque, caixa e recebíveis.
- Repetição de tarefas operacionais e importação manual de arquivos.
- Processos que dependem de sistemas legados sem integração adequada.
- Falta de rastreabilidade sobre quem alterou um dado ou iniciou uma ação.
- Dificuldade de transformar indicadores em próximos passos concretos.

### Perfis de usuário

- **Proprietário/gestor:** acompanha saúde operacional, riscos, caixa, vendas e decisões prioritárias.
- **Operações/estoque:** mantém catálogo, saldos, movimentações, pedidos e logística.
- **Financeiro/compras:** acompanha contas, fornecedores, custos, recebíveis e compromissos.
- **Equipe comercial:** administra clientes, leads, interações, pedidos e resultados.
- **Administrador do tenant:** gerencia usuários, papéis, permissões e integrações.

O produto deve permitir múltiplos usuários e empresas com isolamento de dados por tenant. Permissões de interface são apenas conveniência; a API é sempre a autoridade final.

## 4. Escopo funcional e módulos

Os módulos abaixo representam os domínios do produto. A ordem e a disponibilidade em produção dependem de integração, testes e critérios de aceite — a existência de arquivos ou endpoints isolados não significa que um fluxo completo esteja pronto para usuários.

| Domínio | Responsabilidade principal | Exemplos de capacidades |
|---|---|---|
| Identity, Companies e RBAC | Acesso e contexto empresarial | Usuários, autenticação, papéis, permissões, sessão e tenant ativo |
| CRM | Relacionamento comercial | Clientes, leads, interações e acompanhamento |
| Catálogo e vendas | Operação comercial | Produtos, preços, pedidos, itens e resumo de vendas |
| Inventory | Controle físico | Saldos, movimentações, recebimento e prevenção de inconsistências concorrentes |
| Procurement | Compras e fornecedores | Ordens de compra, custos e visão comparativa de preços |
| Finance | Visibilidade financeira | Caixa, recebíveis, vencimentos e resumos financeiros |
| Logistics | Atendimento e fluxo operacional | Expedição, entregas e acompanhamento logístico |
| Workflow | Coordenação de trabalho | Tarefas, estados, responsáveis e execução de processos |
| Async Processing | Trabalho fora da requisição HTTP | Filas, retentativas, backoff, dead-letter e agendamentos |
| Integrations e Automation | Conectividade e automação | Conexões, health checks, logs, importadores CSV/XLSX e Playwright |
| Notifications | Comunicação operacional | Severidade, leitura/não leitura e notificações persistidas |
| Intelligence | Análise e apoio à decisão | Métricas, evidências, ferramentas de IA, chat e propostas de ação |
| Platform/Observability | Operação e diagnóstico | Saúde, readiness, request IDs, logs estruturados e métricas |

### Princípios de escopo

- Não desenvolver uma tela antes de conhecer o contrato mínimo da API correspondente.
- Não expor como funcional uma ação sem validação, tratamento de erro e feedback para o usuário.
- Priorizar fluxos ponta a ponta sobre a quantidade de telas ou endpoints.
- Usar dados fictícios claramente identificados durante desenvolvimento e demonstrações.
- Adiar funcionalidades especulativas quando não houver dados, regras de negócio ou valor de usuário suficientes.

## 5. Conceitos fundamentais do produto

### 5.1 Modular monolith first

O backend mantém domínios separados dentro de uma aplicação organizada. Serviços compartilhados só devem existir quando uma regra realmente atravessa domínios. Cada módulo deve possuir responsabilidade, modelos, contratos, testes e documentação compreensíveis.

### 5.2 Tenant isolation by default

Toda consulta e operação que envolva dados empresariais deve derivar o tenant do contexto autenticado e validar a autorização no servidor. Nunca confiar em `company_id` enviado pelo cliente sem verificá-lo contra o usuário autenticado. Testes devem procurar tentativas de acesso cruzado entre empresas.

### 5.3 Database is source of truth for persisted jobs

O banco de dados mantém o estado autoritativo dos jobs. Redis é usado como mecanismo de despacho/aceleração, não como único lugar onde um trabalho importante existe. A arquitetura deve suportar recuperação quando Redis fica indisponível.

### 5.4 Contracts before coupling

API, schemas, eventos, jobs, tools de IA e integrações devem ter formatos explícitos e validados. Mudanças incompatíveis precisam de migração, testes e documentação.

### 5.5 Observable by design

Erros relevantes devem gerar logs estruturados com request/job IDs e contexto não sensível. Métricas precisam permitir identificar latência, falhas, backlog, repetição, custo e comportamento dos workers sem registrar segredos.

## 6. Experiências críticas (journeys)

1. **Entrada segura:** usuário cria/seleciona empresa, autentica, vê somente os recursos autorizados e consegue sair da sessão.
2. **Consulta operacional:** usuário abre um módulo, filtra ou pagina dados, entende estados de carregamento/vazio/erro e executa operações com feedback.
3. **Importação controlada:** seleciona CSV/XLSX, valida estrutura, recebe um relatório de erros, executa dry-run e confirma a importação.
4. **Automação confiável:** usuário configura uma integração autorizada, dispara execução assíncrona, acompanha o status e acessa logs/artefatos permitidos.
5. **Consulta com IA:** pergunta em linguagem natural, recebe resposta baseada em ferramentas autorizadas e, quando relevante, vê evidências e limitações.
6. **Ação proposta pela IA:** a IA cria uma proposta; o servidor valida permissões e regras; um humano aprova/rejeita quando exigido; a execução é rastreada por auditoria.
7. **Recuperação de falha:** uma falha de banco, Redis ou integração deixa um estado identificável e recuperável, não um sucesso falso.

## 7. Arquitetura-alvo

```text
React / Vite
    │  HTTP + contratos versionados
    ▼
FastAPI REST API ─── autenticação / RBAC / tenant context / auditoria
    │
    ├── serviços de domínio: CRM, Sales, Inventory, Procurement,
    │                        Finance, Logistics, Workflow, Platform
    ├── Intelligence: métricas, tool registry, gateway, chat, proposals
    ├── Integrations / Automation: importação, Playwright, storage
    └── processamento assíncrono: jobs, workers, scheduler
             │                 │                  │
             ▼                 ▼                  ▼
       PostgreSQL            Redis           Sistemas externos
       fonte persistente     dispatch         / browser automation
             │                                    │
             └──────── storage local / S3 ────────┘

Produção-alvo: contêineres em ECS Fargate, RDS PostgreSQL,
S3 privado, IAM/Secrets Manager, ALB e CloudWatch, com Terraform.
```

### Tecnologias de referência

- **Frontend:** React, Vite, HTML, CSS e JavaScript.
- **API:** Python, FastAPI e REST.
- **Persistência:** PostgreSQL, SQLAlchemy 2 e Alembic.
- **Identidade:** JWT, refresh tokens, RBAC e auditoria.
- **Assíncrono:** Redis, jobs persistidos, workers e scheduler.
- **Integrações:** Playwright, importação CSV/XLSX e adaptadores de storage.
- **Qualidade:** pytest, testes de integração/regressão e GitHub Actions.
- **Ambiente/infraestrutura:** Docker, Compose, AWS e Terraform.
- **Observabilidade:** logs JSON, request IDs, health/readiness e endpoint de métricas Prometheus-compatible.

Tecnologias devem ser adicionadas somente quando resolverem uma necessidade concreta. Não introduzir microsserviços, complexidade de estado ou dependências só por checklist.

## 8. Inteligência artificial: conceito e limites

A IA é uma camada de interpretação e orquestração; não é a fonte primária de verdade financeira, fiscal ou de segurança.

### Arquitetura lógica

```text
Dados de negócio validados
        ↓
Regras determinísticas e analytics
        ↓
Findings / evidências / métricas
        ↓
LLM Gateway (provedor intercambiável)
        ↓
Tool Layer explícita e autorizada
        ↓
Resposta ou proposta de ação
        ↓
Aprovação humana quando necessária
        ↓
Execução pelo backend + validação final
        ↓
Auditoria + resultado + feedback
```

### Regras obrigatórias para IA

- O modelo **não acessa diretamente o banco de dados** nem recebe credenciais de banco.
- Toda leitura de dados passa por tools com schema, validação, tenant isolation, autorização, limites e auditoria.
- Cálculos críticos são feitos por lógica determinística e verificável antes de serem explicados pelo LLM.
- A resposta deve distinguir fato observado, inferência, previsão e incerteza.
- Propostas de impacto financeiro, destrutivo ou externo exigem aprovação explícita de acordo com uma matriz de risco.
- Repetições devem ser controladas por idempotência; ações precisam de timeout, limite de chamadas e política de falhas.
- Não inventar evidências ou afirmar causalidade sem base suficiente.
- Telemetria de IA deve cobrir provedor/modelo, latência, tokens/custo quando disponíveis, tool calls, erros e avaliações, sem vazar dados sensíveis.
- Machine Learning preditivo só entra quando houver histórico adequado, baseline, métricas e avaliação contra falsos positivos.

### Evolução pretendida de IA

1. Catálogo de perguntas e decisões de valor.
2. Regras de negócio com eventos, severidade e evidências.
3. Analytics com KPIs, séries temporais e decomposição de variações.
4. Forecasts e anomalias somente com dados e avaliação adequados.
5. Gateway de LLM independente do fornecedor, com timeout, retry, fallback e limites.
6. Ferramentas controladas e chat persistido.
7. Propostas, aprovação, execução e auditoria.
8. Avaliação contínua de qualidade, utilidade, segurança e custo.

## 9. Segurança, privacidade e governança

- Segredos reais ficam em variáveis de ambiente/secret manager; nunca no Git, frontend, logs ou documentação.
- `.env.example` contém apenas exemplos não sensíveis. Não usar valores de desenvolvimento como segredos de produção.
- Seguir menor privilégio em RBAC e IAM; não atribuir permissões administrativas por conveniência.
- Senhas armazenadas somente com hash seguro. Tokens devem expirar e ser validados no backend.
- Validar tamanho de payloads, upload e arquivos comprimidos; prevenir abuso de CSV/XLSX e importação excessiva.
- Aplicar CORS e trusted hosts configuráveis, headers de segurança, TLS e validação de certificados.
- S3 deve ser privado por padrão, com criptografia, versionamento e URLs assinadas temporárias quando necessárias.
- Produção precisa de backup, retenção e recuperação pontual de banco quando suportada pela configuração escolhida.
- Logs não devem incluir senhas, tokens, credenciais, dados financeiros completos ou arquivos pessoais desnecessários.
- Operações sensíveis devem produzir auditoria com ator, tenant, recurso, ação, horário e resultado.
- Toda mudança de schema é entregue por migration versionada, com plano de rollback ou estratégia segura de forward-fix.

## 10. Identidade visual e experiência de usuário

### 10.1 Direção criativa

**Posicionamento visual:** premium, moderno, tecnológico, sóbrio e orientado a dados. O visual atual da base recuperada segue uma interface dark de produto empresarial, com superfícies azul-marinho quase pretas, texto claro, contornos discretos, cartões com profundidade leve e sinais de status contidos.

A identidade deve transmitir clareza, controle e confiança, não um painel genérico saturado de cores. Preservar a direção visual já existente; não trocar por uma estética substancialmente diferente sem validar antes uma proposta visual com o usuário.

### 10.2 Paleta de referência extraída do frontend atual

Os valores abaixo refletem o CSS encontrado no checkpoint, servindo como tokens iniciais. Devem ser centralizados e contrastados numa futura camada de design tokens antes de uma refatoração visual ampla.

| Token | Cor | Uso atual/pretendido |
|---|---|---|
| `canvas` | `#070A12` | Fundo principal da aplicação |
| `canvas-glow` | `#11182A` | Brilho radial discreto no topo/fundo |
| `surface` | `#0A0E18` | Campos e superfícies internas |
| `surface-raised` | `#0F1420` | Cards, painéis e áreas elevadas |
| `surface-deep` | `#0A0E18` | Base de gradientes de cartões |
| `surface-status` | `#0D111D` | Cartão de status da conexão |
| `text-primary` | `#ECF0FF` | Texto principal e títulos |
| `text-secondary` | `#A9B0C3` | Texto auxiliar e parágrafos |
| `text-muted` | `#7F89A3` | Labels e metadados |
| `text-subtle` | `#6F7891` | Ajuda e informação de baixa prioridade |
| `border` | `#20263A` | Bordas de cards e separadores |
| `border-input` | `#2A3146` | Bordas de campos |
| `focus` | `#5B6EA8` | Foco de teclado/campo ativo |
| `action-primary-bg` | `#E9ECF8` | Botão primário claro |
| `action-primary-text` | `#0C1020` | Texto em botão primário |
| `status-success` | `#47D18C` | Estado concluído/online; sempre acompanhado de texto/ícone |
| `status-neutral` | `#7D8496` | Estado neutro/desconhecido |
| `status-warning` | `#E9B949` | Atenção/aguardando |
| `status-error` | `#E85D75` | Falha/erro/offline |
| `error-surface` | `#24121B` | Fundo de feedback de erro |
| `error-border` | `#633044` | Borda de feedback de erro |

**Regra de uso:** cores de status comunicam estado e não devem ser escolhidas apenas para decoração. Verde, amarelo e vermelho/rosa devem manter significado consistente. Não introduzir cores fortes para cada módulo sem necessidade. Acessibilidade/contraste deve ser verificada antes de congelar os tokens.

### 10.3 Tipografia

- Fonte atual: `Inter` com fallback para `ui-sans-serif`, `system-ui` e fontes nativas.
- Priorizar legibilidade, números claros e hierarquia tipográfica consistente.
- Títulos curtos e fortes; metadados e labels menores, discretos e com contraste suficiente.
- Evitar muitas famílias, pesos ou tamanhos concorrentes.
- Tabelas financeiras/indicadores devem alinhar números e facilitar comparação.

### 10.4 Forma, espaço e profundidade

- Conteúdo em canvas escuro, painéis em superfícies ligeiramente mais claras, bordas azul-acinzentadas finas.
- Cantos arredondados atuais: aproximadamente 11 px em controles, 14 px em cartões de status e 18–22 px em painéis de maior destaque.
- Sombras discretas, sem glow excessivo ou efeitos de vidro que prejudiquem contraste.
- Espaçamento consistente, grupos visuais claros e densidade adequada para uso operacional.
- Grids e tabelas devem escalar em telas pequenas por responsividade/rolagem controlada, nunca por truncamento silencioso de dados importantes.

### 10.5 Componentes e padrões de interação

Criar uma biblioteca reutilizável de Button, Input, Select, Modal, Badge, Card, Table, Spinner, Alert/Toast, Empty State, Breadcrumb, Sidebar, Header, Pagination e Confirmation Dialog. Cada padrão deve ter estados normal, hover, focus, disabled, loading e error quando aplicável.

Toda tela que consulta API deve explicitar estados de **carregamento, sucesso, vazio, erro e nova tentativa** quando cabível. Ações críticas pedem confirmação, e operações assíncronas precisam mostrar progresso/status e permitir consulta posterior.

### 10.6 Layout da aplicação

- Shell empresarial com navegação lateral, header, contexto da empresa, conteúdo principal e breadcrumbs quando ajudarem orientação.
- Dashboard com KPIs, alertas, atividade recente e atalhos — somente com dados reais da API ou exemplos claramente sinalizados.
- Páginas operacionais priorizam filtros, busca, ordenação, paginação, detalhe do registro e ações pertinentes à permissão.
- Chat de IA deve exibir fontes/evidências disponíveis, limites conhecidos e estado de ações/propostas, não apenas uma bolha de conversa.
- Autenticação deve manter o mesmo sistema visual e hierarquia, sem parecer produto separado.

### 10.7 Responsividade e acessibilidade

- Suporte inicial: desktop e tablet, com layouts utilizáveis em mobile para operações essenciais.
- Teclado funcional, foco visível, rótulos associados aos campos, mensagens de erro compreensíveis e alternativas textuais aos indicadores por cor.
- Sem ações acessíveis somente por hover; alvos de toque adequados; tabelas com estratégia mobile deliberada.
- Respeitar preferência por movimento reduzido e evitar animações que interfiram na operação.
- Realizar verificações de contraste com ferramentas antes de declarar conformidade WCAG.

### 10.8 Voz e linguagem

- Linguagem profissional, direta, clara e não alarmista.
- Em erro, dizer o que aconteceu e qual é a próxima opção segura.
- Não exibir stack traces, tokens, nomes internos de serviços ou conteúdo técnico cru para usuários finais.
- Idioma inicial sugerido para a interface: português brasileiro; preparar internacionalização sem hardcode de texto em componentes quando isso se tornar necessário.
- A IA deve declarar incerteza e diferenciar dados observados de interpretação.

### 10.9 Marca e ativos ainda não definidos

O nome do produto é **NEXUS** e o conceito visual atual está refletido no frontend. Logotipo definitivo, conjunto de ícones, ilustrações, regras de fotografia e brand book formal ainda precisam de decisão explícita; não considerar nenhum desses ativos finalizados apenas com base na paleta existente.

## 11. Plano técnico por trilha

### 11.1 Backend — baseline B0–B9

O checkpoint `v0.18.0 — B9 Cloud` inclui uma implementação ampla de backend: API FastAPI, domínios empresariais, identidade/RBAC/auditoria, SQLAlchemy/Alembic, jobs, integrações, API de inteligência, testes e artefatos de cloud.

| Fase | Objetivo | Estado histórico | Confirmação obrigatória na retomada |
|---|---|---|---|
| B0 | Fundação técnica | Implementada | Executar CI/testes atuais |
| B1 | Persistência PostgreSQL/SQLAlchemy/Alembic | Parcial: runtime PostgreSQL do NEXUS pendente | Rodar migrations reais, `alembic current` e suíte contra PostgreSQL |
| B2 | Identity, segurança, RBAC e auditoria | Implementada no checkpoint | Regressão de autenticação, tenant isolation e permissões |
| B3 | Domínios core | Implementados no checkpoint | Fluxos integrados e invariantes de negócio |
| B4 | Contratos/plataforma | Implementada no checkpoint | Contratos e endpoints coerentes com frontend |
| B5 | Async jobs, retry, dead-letter e scheduler | Implementada/testada historicamente | Validar recuperação, idempotência e Redis indisponível |
| B6 | Integrações, Playwright, importação e storage | Implementada/testada historicamente | Testar timeout, allowlist, tamanho de arquivo e falhas externas |
| B7 | Intelligence API, tools, gateway, chat e approvals | Implementada/testada historicamente | Validar provider real, autorização das tools e ciclo de aprovação |
| B8 | Qualidade, segurança e observabilidade | Implementada/testada historicamente | Rodar suíte completa, CI, logs, métricas e testes concorrentes |
| B9 | Infraestrutura cloud | Código/artefatos preparados | Validar configuração e deployment real somente com acesso/credenciais AWS autorizados |

Números de testes citados em checkpoints anteriores são históricos, não resultado da execução nesta retomada. Reexecutar antes de declarar o status verde.

### 11.2 Frontend

O checkpoint contém React/Vite e uma interface inicial. A estrutura-alvo é modular por funcionalidades: `auth`, `dashboard`, `crm`, `sales`, `inventory`, `procurement`, `finance`, `logistics`, `workflow`, `automation` e `intelligence`, além de `components/ui`, serviços HTTP, stores/hooks, configuração e testes.

Sequência planejada:

1. **F0 — Fundação:** comandos locais, configuração por ambiente, estrutura, tokens visuais e shell responsivo.
2. **F1 — API:** cliente HTTP centralizado, contratos/tipos, handling de erros e estados de dados.
3. **F2 — Identity:** login/cadastro, sessão, logout, rotas protegidas, contexto de empresa e permissões visuais.
4. **F3 — Dashboard/Platform:** KPIs, alertas, notificação, tabelas, busca, paginação e filtros.
5. **F4 — CRM/Sales:** clientes, leads, interações, produtos e pedidos conectados à API.
6. **F5 — Inventory/Procurement:** saldos, movimentações, fornecedores, compras e validações.
7. **F6 — Finance/Logistics:** caixa, recebíveis, status e fluxos operacionais.
8. **F7 — Workflow/Automation:** tarefas, importações, integração, progresso de jobs e logs.
9. **F8 — Intelligence:** chat, evidências, ferramentas permitidas, propostas e aprovações.
10. **F9 — Polimento:** acessibilidade, responsividade, estados, testes de interface, desempenho e consistência visual.

Não marcar fases como concluídas apenas por existirem componentes ou placeholders. Cada fluxo deve usar contratos reais e ter testes/aceite.

### 11.3 IA/Intelligence

Sequência de evolução:

- I0: catálogo de casos de uso, taxonomia de eventos, schemas para findings/evidências/recomendações/propostas e telemetria.
- I1: rules engine determinístico com severidade, cooldown e evidências.
- I2: KPIs, séries temporais, decomposição de variações e explicabilidade.
- I3: forecast/anomalias somente quando houver volume/qualidade de dados e avaliação definida.
- I4: gateway de LLM com provedores intercambiáveis, limites, timeout, retry e fallback.
- I5: tool layer com schemas, autorização, tenant scope e auditoria.
- I6: chat com histórico e contexto controlado.
- I7: proposals, aprovação humana, execução segura, idempotência e auditoria.
- I8: avaliação em datasets de referência, guardrails, métricas e monitoramento contínuo.

A base de gateway, provider Mock/OpenAI-compatible, tools, chat e action approvals consta no checkpoint B7; o estado de integração real deve ser provado por testes e configuração válidos, sem pressupor que já esteja pronto para produção.

## 12. Infraestrutura e implantação

### Ambiente de desenvolvimento

- Windows + PowerShell como ambiente observado da retomada.
- Docker e Docker Compose disponíveis na máquina, conforme validação anterior.
- `backend/requirements.txt` define dependências da API e testes.
- `frontend/package.json` usa React/Vite.
- `.env.example` é a referência de variáveis; criar `.env` local sem versioná-lo.

### Arquitetura de produção planejada

- Imagem de backend executada em serviços separados de API, worker e scheduler.
- ECS Fargate para execução de contêineres.
- RDS PostgreSQL em subnets privadas, com criptografia e estratégia de backup.
- S3 privado com bloqueio de acesso público, criptografia, versionamento e URLs assinadas temporárias.
- IAM de menor privilégio e AWS Secrets Manager.
- ALB, CloudWatch Logs/metrics e health checks.
- Terraform para infraestrutura como código.

**Não há confirmação de deploy real na AWS no checkpoint.** Código Terraform e imagens preparadas não significam infraestrutura provisionada, segura ou testada em ambiente real.

## 13. Qualidade e critérios de conclusão

Uma microtarefa só pode ser marcada como concluída depois de:

1. Dependências e pré-requisitos verificados.
2. Implementação feita no local correto, seguindo a arquitetura.
3. Testes unitários e/ou de integração pertinentes adicionados ou atualizados.
4. Testes executados e resultados observados.
5. Erros e regressões corrigidos.
6. Migrações/contratos/documentação atualizados quando necessários.
7. Regressão relevante executada.
8. Segurança, tenant isolation e dados sensíveis revisados.
9. Resultado registrado no master plan e/ou plano da trilha.
10. Commit criado com escopo claro e árvore de trabalho revisada.

### Portas de qualidade para uma versão utilizável

- **Gate A — Persistência:** migrations completas, DB saudável, backup/restore testado e suíte no banco de produção-alvo.
- **Gate B — Segurança:** autenticação/RBAC/tenant isolation confirmados por testes negativos e positivos; configuração de produção segura.
- **Gate C — Fluxos de negócio:** jornadas críticas passam ponta a ponta sem depender de mocks, exceto nos testes planejados.
- **Gate D — Frontend:** loading/empty/error/success, responsividade, acessibilidade básica, manejo de sessão e feedback confiáveis.
- **Gate E — Assíncrono/integrações:** jobs recuperáveis, idempotentes, auditáveis e limitados; falhas externas tratadas.
- **Gate F — IA:** tools autorizadas, evidências corretas, aprovação de ações sensíveis, limites de custo/tempo e avaliação documentada.
- **Gate G — Operação:** health/readiness, logs, métricas, alertas, backups, secrets e runbooks verificados.
- **Gate H — Release:** testes completos, revisão de mudanças, documentação de release, rollback/forward-fix e versão identificável.

## 14. Fluxo de desenvolvimento e Git

### Estrutura de trabalho

- Branch principal: `main`.
- Usar branches pequenas para features/fixes quando possível: `feat/<tema>`, `fix/<tema>`, `docs/<tema>`, `chore/<tema>`.
- Commits objetivos, preferencialmente no formato Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Não fazer push de `.env`, credenciais, banco de dados real, Terraform state, arquivos de build ou dados operacionais.
- Revisar `git status`, diff e arquivos staged antes de cada commit.
- Não usar `reset --hard`, `clean -fd`, force push ou comandos destrutivos sem motivo claro e confirmação sobre dados que podem ser perdidos.
- Não assumir que o conteúdo de um ZIP possui o histórico anterior; o checkpoint recuperado foi inicializado como novo repositório local.
- O remoto oficial planejado é `https://github.com/hik4s/NEXUS.git`; a presença/permissão do repositório deve ser reconfirmada antes do push. O primeiro commit local de recuperação foi `e46cdcb` antes da inclusão deste documento.

### Regra operacional

Trabalhar em modo incremental, mas contínuo. Não parar por erros comuns: diagnosticar, corrigir e repetir testes. Parar somente quando faltar acesso/credencial indispensável, houver risco material para dados, existir uma decisão irreversível de produto/arquitetura ou for necessária uma escolha humana.

## 15. Backlog de retomada — ordem obrigatória

1. Confirmar a integridade do checkpoint e o status Git/remoto.
2. Publicar o baseline recuperado e este master plan no repositório remoto autorizado.
3. Validar o estado de Docker/Compose e a disponibilidade dos serviços necessários.
4. Executar as migrations Alembic reais contra PostgreSQL do projeto; validar `alembic current`, upgrade e estratégia de rollback.
5. Executar todos os testes backend e corrigir regressões sem mascarar falhas.
6. Validar Redis/jobs/scheduler: retry, idempotência, dead-letter, recuperação quando Redis está indisponível e jobs recorrentes.
7. Auditar isolamento multi-tenant, RBAC, endpoints sensíveis, upload/importação, secrets e logs.
8. Executar testes integrados API ↔ PostgreSQL ↔ frontend para jornadas críticas.
9. Evoluir frontend conforme F0–F9 e preservar a direção visual dark atual.
10. Validar provedor real de IA apenas com credencial autorizada; conferir tools, limites, logs e aprovação.
11. Revisar Terraform/Compose em ambiente seguro; provisionar AWS somente com autorização, orçamento e credenciais explícitas.
12. Rodar gate de release, registrar evidências, atualizar este documento e criar checkpoint versionado.

### Estado conhecido na retomada

- Recuperado localmente de `NEXUS-v0.18-b9-cloud.zip`.
- Repositório Git local reconstituído em `C:\Users\hikas\Downloads\NEXUS`, branch `main`.
- Commit inicial de recuperação: `e46cdcb`.
- `.gitignore` reforçado e `.gitattributes` adicionados.
- B1 ainda requer migrations e testes reais do NEXUS em PostgreSQL.
- AWS real continua sem validação neste checkpoint.
- O histórico Git anterior ao ZIP não foi recuperado; o commit inicial é um novo ponto de partida.
- A interface e a integração real de IA requerem avaliação funcional integrada; não assumir completude de produto.

## 16. O que o NEXUS não deve se tornar

- Um conjunto de módulos desconectados que compartilham só a barra lateral.
- Um dashboard estático que aparenta funcionamento sem dados reais.
- Um LLM com acesso direto ao banco, permissão irrestrita ou capacidade de executar mudanças críticas sem política de aprovação.
- Um projeto distribuído em microsserviços antes de existir uma necessidade comprovada.
- Uma coleção de dependências introduzidas somente para parecer sofisticado.
- Um sistema que considera tarefas concluídas apenas porque o código compila ou existe um teste unitário isolado.
- Uma interface que sacrifica contraste, acessibilidade ou legibilidade por estética.
- Uma implantação em produção sem secrets seguros, backups, observabilidade e rollback.

## 17. Decisões que precisam de registro explícito

Manter um ADR ou seção de decisões para escolhas que impactam compatibilidade ou segurança, incluindo:

- Política final de localização/idioma, moeda e fuso horário por tenant.
- Matriz de risco e aprovação das ações da IA.
- Política de retenção de dados, logs, importações e arquivos.
- Provedor(es) de LLM, orçamento e política de fallback.
- Escopo do MVP/piloto, personas prioritárias e metas de sucesso mensuráveis.
- Logotipo e ativos formais de marca, além da identidade visual já presente no CSS.
- Estratégia operacional de backups, alertas, recuperação e suporte.

Nenhuma escolha importante deve ser inferida como decisão final só porque existe um valor padrão ou uma implementação inicial.

## 18. Glossário

- **Tenant:** empresa/unidade cujo conjunto de dados e permissões deve permanecer isolado.
- **RBAC:** controle de acesso baseado em papéis e permissões.
- **Job:** trabalho persistido para execução assíncrona.
- **Dead-letter:** estado/fila para jobs que excederam a política de tentativas e exigem diagnóstico.
- **Tool Layer:** funções de negócio permitidas à IA, com contratos e autorização; não é acesso direto ao banco.
- **Finding/Evidence:** problema identificado e os dados verificáveis que sustentam a conclusão.
- **Action Proposal:** proposta registrada que pode exigir aprovação humana antes da execução.
- **Gate:** conjunto de critérios verificáveis necessário para avançar uma fase ou publicar uma versão.
- **Checkpoint:** artefato versionado e identificável que permite recuperar uma etapa do trabalho.

## 19. Histórico deste documento

### Alinhamento de retomada — 2026-10-26

- Modelo aprovado: aplicação web hospedável em domínio próprio e aplicativo desktop futuro para Windows, macOS e Linux, compartilhando backend, contas e banco central.
- Uso offline com armazenamento local e sincronização ao reconectar faz parte da direção aprovada. Conflitos de edição devem permitir decisão humana, sem sobrescrita silenciosa. Escopo offline, regras por operação e tecnologia desktop ainda precisam de desenho detalhado.
- Ordem incremental: estabilizar a base e entregar jornadas web completas; depois hospedagem, desktop e capacidades offline. Preparar contratos e dados para sincronização sem antecipar sua implementação.
- Auditoria do baseline: 66 testes backend aprovados em SQLite (Python 3.12), com um aviso de depreciação de Starlette/TestClient. Isso não valida PostgreSQL, Redis, provedor real de IA ou AWS.
- Reproduzida falha de CI: `alembic check` em banco vazio retorna `Target database is not up to date`. Aplicar `alembic upgrade head` antes do check elimina o bloqueio no ensaio local em SQLite. Execução remota do workflow corrigido ainda pendente.
- Próximo bloco: validar migrations e testes em PostgreSQL, seguido de Redis/jobs e da primeira jornada web integrada. O frontend permanece inicial; não considerar F0–F9 concluídos.
- Continuação: workflow preparado para PostgreSQL 17 e Redis 8 reais, além da regressão SQLite; teste Redis opt-in verifica publicação, ordem e consumo sem mock e usa chave isolada. Sua execução remota ainda precisa ser observada.
- Frontend: `package-lock.json` gerado para instalação reproduzível e workflow de build acrescentado. `npm ci --ignore-scripts` e `npm run build` passaram localmente. Isso não comprova jornadas de interface.
- Verificação local atual: migrations em banco SQLite novo, `alembic check` sem diferenças, 66 testes aprovados e 1 teste Redis explicitamente ignorado por ausência do serviço; 1 aviso de depreciação de dependência.
- Correções seguintes, reproduzidas primeiro por testes: job em execução não pode ser executado novamente; claim usa atualização condicional de `queued` para `running`; execução manual de job não disponível retorna HTTP 409; tick manual do scheduler é limitado à empresa autenticada (scheduler de serviço permanece global).
- Regressão após as correções: 69 testes aprovados, 1 teste Redis ignorado e 1 aviso de depreciação; migrations e Alembic check passaram em SQLite novo. PostgreSQL/Redis reais permanecem pendentes.
- Publicação da branch bloqueada pela revisão automática de autorização para envio externo de código ao GitHub. Commits locais não comprovam execução remota; obter autorização específica antes de repetir o push.

- **1.0 — 2026-10-10:** consolidada visão do produto, conceitos arquiteturais, objetivos, identidade visual baseada no frontend do checkpoint v0.18, trilhas, gates de qualidade, estado conhecido e plano de retomada.

---

**Fonte de verdade:** este documento descreve intenção, regras e critérios globais do projeto. Os roadmaps `NEXUS-roadmap/01-FRONTEND.md`, `02-BACKEND.md` e `03-IA.md` mantêm o detalhe por trilha. Em caso de divergência, registrar a decisão e atualizar os documentos; nunca marcar uma etapa como concluída sem evidência verificável.
