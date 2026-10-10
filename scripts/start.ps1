$ErrorActionPreference = "Stop"

if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host ".env created from .env.example"
}

docker compose up --build
