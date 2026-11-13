# NEXUS — Supabase Auth e acesso livre

Autorizado: Google/GitHub/e-mail, acesso livre e sem convites. Entrar deve bastar.
Projeto NEXUS Auth mszdilxysgnmkyekknat confirmado; providers ativos, confirmação
por e-mail ativa, assinatura ES256 no JWKS.

Decisão: Supabase identifica; FastAPI valida JWT e resolve RBAC/dados no Neon.
Evitar trocar por outro JWT Nexus (duas sessões) ou migrar dados de negócio sem
necessidade. Primeiro login cria empresa privada e usuário administrador dela,
atomicamente e de forma idempotente pelo subject. Não associar por e-mail nem
confiar em user_metadata para permissões. Contas legadas preservadas; colisões de
e-mail exigem migração explícita. Convites ficam para etapa posterior.

React: PKCE para Google/GitHub; e-mail/senha com cadastro, confirmação, recuperação,
atualização de senha, renovação e saída. Sessão bearer por aba em sessionStorage;
canal SDK aleatório por instância. Apenas provas PKCE temporárias por fluxo ficam
no localStorage por até uma hora para callback em nova aba, nunca bearer tokens. Callback permitido, parâmetros removidos da URL, nenhuma chave
secreta/service_role no cliente. Backend modo legacy|supabase; modo Supabase não
emite/renova JWT local. JWKS cacheado/timeout, validação de issuer/audience/exp/sub.

Critérios: tokens inválidos/projeto errado, empresa isolada, bootstrap concorrente,
regressões SQLite/PostgreSQL, UI/login/logout/refresh e E2E. Providers habilitados
não equivalem a OAuth real homologado: conferir callbacks publicados. Só atualizar
M6/release mediante evidências de execução. Melhorias de interface e jornada vêm
após autenticação; IA/AWS/convites continuam evoluções separadas.
