# Automation

B6 concentra integrações externas e automações desacopladas do processo HTTP.

- `playwright_executor.py`: navegação/screenshot em worker.
- `app.workers.handlers`: registra `playwright.capture_page` e `import.customers`.
- Jobs persistem no banco antes de serem despachados.
- Em produção, aplicar allowlist de hosts e políticas de egress.
