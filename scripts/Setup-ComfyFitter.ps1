$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$appPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
Push-Location $projectRoot
try {
    if (!(Test-Path -LiteralPath $appPython)) {
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Application environment creation failed.' }
    }
    & $appPython -m pip install -r backend\requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Application dependency installation failed.' }
    Push-Location (Join-Path $projectRoot 'frontend')
    try {
        & npm.cmd ci --no-fund --no-audit
        if ($LASTEXITCODE -ne 0) { throw 'Browser dependency installation failed.' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Browser build failed.' }
    } finally { Pop-Location }
} finally { Pop-Location }
Write-Host 'Application setup complete. ComfyUI and its models remain separate prerequisites; see docs\SETUP.md.'
