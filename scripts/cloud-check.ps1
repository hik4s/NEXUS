$ErrorActionPreference = 'Stop'

Write-Host "=== NEXUS Cloud prerequisite check ==="

$commands = @('terraform', 'aws', 'docker')
foreach ($command in $commands) {
    $found = Get-Command $command -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "[OK] $command -> $($found.Source)"
    } else {
        Write-Host "[MISSING] $command"
    }
}

Write-Host ""
Write-Host "Terraform files:" 
Get-ChildItem -Path "$PSScriptRoot\..\infra\terraform" -Filter *.tf | ForEach-Object { Write-Host " - $($_.Name)" }
