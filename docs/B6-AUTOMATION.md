# NEXUS — B6 Automation & Integrations

## Scope

- Integration connections and health status.
- Encrypted credential storage.
- Integration logs.
- Local/S3 file storage abstraction.
- CSV/XLSX customer import with validation and dry-run.
- Import execution through background jobs.
- Playwright capture executed only by workers, never inside HTTP requests.

## Architecture

```text
HTTP API
  ├── IntegrationConnection
  ├── FileAsset
  └── ImportRun
        ↓
BackgroundJob
        ↓
Worker
  ├── import.customers
  └── playwright.capture_page
        ↓
LocalStorage / S3Storage
```

## Security decisions

- Credentials are encrypted at rest and never returned by API responses.
- File access is tenant-scoped.
- Playwright accepts navigation tasks, not arbitrary Python/shell execution.
- Production deployments should restrict outbound network access and use an explicit host allowlist.
- Redis is not the source of truth for jobs; the database remains authoritative.

## Current validation boundary

The local storage backend and importers are tested locally. The S3 and Playwright browser integrations are implemented behind adapters, but their live cloud/browser runtime still requires their external services/runtime assets.
