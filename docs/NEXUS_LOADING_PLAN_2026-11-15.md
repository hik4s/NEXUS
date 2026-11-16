# Autenticação e carregamento — 15/11/2026

Escopo autorizado pela continuação do NEXUS: concluir duas evoluções já registradas no handoff.

1. Testar e remover provas PKCE vencidas ou inválidas ao iniciar o adaptador e um novo fluxo; preservar provas válidas e dados de outras aplicações.
2. Separar o workspace em importação dinâmica após autenticação, com estado de carregamento e mensagem recuperável se o download falhar.
3. Validar testes, tipos, build Supabase e fluxos de navegador; revisar o diff antes da integração.
4. Atualizar documentação com evidências e registrar o teste OAuth relatado pelo usuário sem atribuir observação independente.

Sem mudanças no banco, template de e-mail ou credenciais. Sessões continuam por aba.

## Evidências

- Suite frontend: 45 testes aprovados; caso adicional de leitura inválida após inicialização: 8/8 testes de armazenamento aprovados (46 testes no total).
- TypeScript e build Supabase aprovados: entrada 473,20 kB; Workspace 48,32 kB (gzip 135,97/11,26 kB).
- Playwright: 2/2 jornadas PostgreSQL aprovadas, incluindo ausência de requisição do workspace antes do login e carregamento posterior.
- Revisão independente: corrigida mensagem sobre sessão no modo legado e validação numérica/finita na leitura de provas.
- Teste OAuth: usuário relatou ambos os provedores abrindo workspace. Consulta read-only à conta informada mostrou apenas email; sem confirmação independente das identidades sociais.

O smoke local do build usa contas sintéticas no provedor/API reais sem enviar e-mail. O navegador isolado ignora CORS somente neste ensaio porque a origem local não está autorizada em produção. Não constitui teste de CORS. As primeiras tentativas sem URL de API correta/sem origem autorizada falharam e removeram suas contas de teste.

Smoke local concluído: falha de download exibiu alerta; recarregar abriu workspace. Código, link, reload e mobile aprovados; limpeza de contas sintéticas confirmada.
