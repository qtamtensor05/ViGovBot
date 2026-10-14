param(
    [switch]$NoBrowser,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv-qlora\Scripts\python.exe"
$logDir = Join-Path $projectRoot "outputs\qlora"
$controlDir = Join-Path $logDir "control\tensorboard"
$pidPath = Join-Path $controlDir "pid.txt"
$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*tensorboard*" -and $_.CommandLine -like "*--port 6006*"
}
if ($existing) { throw "TensorBoard is already configured on port 6006, PID=$($existing.ProcessId)." }
if ($DryRun) {
    Write-Output "DRY_RUN: $python -m tensorboard.main --logdir $logDir --host 127.0.0.1 --port 6006"
    exit 0
}
New-Item -ItemType Directory -Path $controlDir -Force | Out-Null
$process = Start-Process -FilePath $python -ArgumentList @("-m", "tensorboard.main", "--logdir", $logDir, "--host", "127.0.0.1", "--port", "6006") `
    -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $controlDir "stdout.log") -RedirectStandardError (Join-Path $controlDir "stderr.log")
$process.Id | Set-Content -LiteralPath $pidPath -Encoding ascii
Write-Host "TensorBoard PID=$($process.Id): http://localhost:6006"
if (-not $NoBrowser) { Start-Process "http://localhost:6006" | Out-Null }
