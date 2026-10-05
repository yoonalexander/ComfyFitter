param([Parameter(Mandatory=$true)][string]$OwnerEmail)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $projectRoot
try {
    & (Join-Path $projectRoot '.venv\Scripts\python.exe') -m scripts.web_runtime start --allowed-email $OwnerEmail
    if ($LASTEXITCODE -ne 0) { throw 'Protected web connection did not start. Local application was preserved.' }
} finally { Pop-Location }
