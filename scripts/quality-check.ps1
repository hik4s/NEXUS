$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\backend")

python -m compileall -q app
python -m alembic check
python -m pytest -q
