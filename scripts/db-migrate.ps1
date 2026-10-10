$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\backend")
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "sqlite:///./data/nexus.db"
}

python -m alembic upgrade head
