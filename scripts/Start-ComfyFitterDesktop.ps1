$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$appPython = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
if (!(Test-Path -LiteralPath $appPython)) { throw 'Run scripts\Setup-ComfyFitterDesktop.ps1 first.' }
$logDir = Join-Path $projectRoot '.local\logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Start-Process -FilePath $appPython -WorkingDirectory $projectRoot -WindowStyle Hidden -ArgumentList @('-m','desktop.app') -RedirectStandardOutput (Join-Path $logDir 'desktop-window.stdout.log') -RedirectStandardError (Join-Path $logDir 'desktop-window.stderr.log')
