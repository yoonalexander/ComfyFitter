$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $projectRoot
try {
    & (Join-Path $projectRoot '.venv\Scripts\python.exe') -m scripts.web_runtime stop
    if ($LASTEXITCODE -ne 0) { throw 'Process ownership did not verify. Inspect the private launcher record.' }
} finally { Pop-Location }
