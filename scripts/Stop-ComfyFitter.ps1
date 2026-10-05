$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$statePath = Join-Path $projectRoot '.local\application-process.json'
if (!(Test-Path -LiteralPath $statePath)) { Write-Host 'No launcher-owned application process is recorded.'; exit 0 }
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$ownedProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($state.processId)" -ErrorAction SilentlyContinue
if ($ownedProcess) {
    if (!$ownedProcess.CommandLine.Contains('uvicorn backend.app.main:app') -or
        !$ownedProcess.CommandLine.Contains("--port $($state.port)") -or
        !$ownedProcess.CommandLine.Contains($state.python)) {
        throw 'The recorded PID no longer matches this launcher-owned application. It was preserved.'
    }
    Stop-Process -Id $state.processId
    Write-Host 'ComfyFitter application stopped. Any submitted ComfyUI generation continues independently.'
} else { Write-Host 'The recorded application process is already stopped.' }
Remove-Item -LiteralPath $statePath
