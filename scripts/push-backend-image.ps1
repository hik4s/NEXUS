param(
    [Parameter(Mandatory=$true)][string]$Repository,
    [string]$Tag = "0.18.0"
)

$ErrorActionPreference = 'Stop'

$image = "$Repository`:$Tag"
docker build -t $image ./backend
docker push $image
