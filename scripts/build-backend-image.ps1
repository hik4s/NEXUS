param(
    [string]$Tag = "0.18.0"
)

$ErrorActionPreference = 'Stop'

docker build -t "nexus-backend:$Tag" ./backend
