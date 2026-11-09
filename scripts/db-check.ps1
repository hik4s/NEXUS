param([string]$PythonExecutable)

$ErrorActionPreference = "Stop"
if (-not $env:DATABASE_URL) {
    throw "Set DATABASE_URL explicitly to a disposable PostgreSQL database."
}
if (-not $env:DATABASE_URL.StartsWith("postgresql+psycopg://")) {
    throw "M0 requires postgresql+psycopg; SQLite is not a substitute."
}
if (-not $PythonExecutable) {
    $PythonExecutable = Join-Path $PSScriptRoot "..\backend\.venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $PythonExecutable)) { $PythonExecutable = "python" }
}
Push-Location (Join-Path $PSScriptRoot "..\backend")
try {
    & $PythonExecutable -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Migration failed." }
    & $PythonExecutable -m alembic check
    if ($LASTEXITCODE -ne 0) { throw "Schema drift detected." }
    & $PythonExecutable -m alembic current
    if ($LASTEXITCODE -ne 0) { throw "Cannot read migration revision." }
} finally {
    Pop-Location
}
