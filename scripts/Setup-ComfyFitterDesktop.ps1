param([string]$ComfyRoot)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $PSScriptRoot 'Setup-ComfyFitter.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Application setup failed.' }
$appPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $appPython -m pip install -r (Join-Path $projectRoot 'desktop\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Desktop dependency installation failed.' }
$desktopDir = Join-Path $projectRoot '.local\desktop'
New-Item -ItemType Directory -Path $desktopDir -Force | Out-Null
if ($ComfyRoot) {
    $resolvedRoot = (Resolve-Path -LiteralPath $ComfyRoot).Path
    if (!(Test-Path -LiteralPath (Join-Path $resolvedRoot 'main.py'))) { throw 'Choose an existing ComfyUI installation folder.' }
    @{ comfy_root=$resolvedRoot } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $desktopDir 'config.json') -Encoding utf8
}
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'ComfyFitter.lnk'))
$shortcut.TargetPath = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot 'Start-ComfyFitterDesktop.ps1') + '"'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.WindowStyle = 7
$shortcut.Description = 'Local ComfyFitter desktop fitting room'
$shortcut.Save()
Write-Host 'Desktop setup complete. Open the ComfyFitter desktop shortcut. Existing ComfyUI models are reused.'
