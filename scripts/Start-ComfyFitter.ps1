param([ValidateRange(1024,65535)][int]$Port = 8000, [switch]$NoBrowser, [string]$ProtectionPython)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimePath = Join-Path $projectRoot '.local\application-runtime.json'
if ($ProtectionPython) {
    if (!(Test-Path -LiteralPath $ProtectionPython -PathType Leaf)) { throw 'The provided source-protection interpreter does not exist.' }
    $env:COMFYFITTER_PROTECTION_PYTHON = (Resolve-Path -LiteralPath $ProtectionPython).Path
    New-Item -ItemType Directory -Path (Join-Path $projectRoot '.local') -Force | Out-Null
    @{ protectionPython=$env:COMFYFITTER_PROTECTION_PYTHON } | ConvertTo-Json | Set-Content -LiteralPath $runtimePath -Encoding utf8
} elseif (!$env:COMFYFITTER_PROTECTION_PYTHON -and (Test-Path -LiteralPath $runtimePath)) {
    $runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
    if ($runtime.protectionPython -and (Test-Path -LiteralPath $runtime.protectionPython -PathType Leaf)) { $env:COMFYFITTER_PROTECTION_PYTHON=$runtime.protectionPython }
}
$appPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$index = Join-Path $projectRoot 'frontend\dist\index.html'
if (!(Test-Path -LiteralPath $appPython) -or !(Test-Path -LiteralPath $index)) {
    throw 'Application dependencies or browser build are missing. Run scripts\Setup-ComfyFitter.ps1 first.'
}
$url = "http://127.0.0.1:$Port"
$health = $null
try { $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 5 } catch { }
if ($health -and $health.application -ne 'comfyfitter') { throw "Port $Port is used by another application. Choose a different -Port." }
if (!$health) {
    $logDir = Join-Path $projectRoot '.local\logs'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $process = Start-Process -FilePath $appPython -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
        -ArgumentList @('-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',"$Port",'--workers','1','--no-access-log') `
        -RedirectStandardOutput (Join-Path $logDir 'application.stdout.log') -RedirectStandardError (Join-Path $logDir 'application.stderr.log')
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        try { $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 5; if ($health.application -eq 'comfyfitter') { break } } catch { }
        if ($process.HasExited) { throw "Application startup failed. See .local\logs\application.stderr.log." }
        Start-Sleep -Milliseconds 250
    }
    if (!$health -or $health.application -ne 'comfyfitter') { throw 'Application readiness was not confirmed. Inspect the application log before retrying.' }
    @{ processId = $health.process_id; launcherProcessId = $process.Id; port = $Port; url = $url; python = $appPython } |
        ConvertTo-Json | Set-Content (Join-Path $projectRoot '.local\application-process.json') -Encoding utf8
}
Write-Host "ComfyFitter: $url"
if ($health.comfyui.ready) { Write-Host 'Image service: ready' }
else { Write-Host ('Image service: ' + $health.comfyui.error.message) }
if (!$health.supported_categories.Count) { Write-Host 'Generation is disabled until the selected workflow passes its full quality gate.' }
if (!$NoBrowser) { Start-Process $url }
