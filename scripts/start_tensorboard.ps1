param(
    [string]$RunId = "",
    [int]$Port = 6006,
    [string]$PythonPath = "",
    [switch]$NoBrowser,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = if ($PythonPath) { [System.IO.Path]::GetFullPath($PythonPath) } else { Join-Path $projectRoot ".venv-qlora\Scripts\python.exe" }
$outputRoot = Join-Path $projectRoot "outputs\qlora"
$logDir = if ($RunId) { Join-Path $outputRoot $RunId } else { $outputRoot }
$controlDir = Join-Path $logDir "control\tensorboard"
$pidPath = Join-Path $controlDir "pid.txt"
$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*tensorboard*" -and $_.CommandLine -like "*--port $Port*"
}
if ($existing) { throw "TensorBoard is already configured on port $Port, PID=$($existing.ProcessId)." }
if ($DryRun) {
    Write-Output "DRY_RUN: $python -m tensorboard.main --logdir $logDir --host 127.0.0.1 --port $Port"
    exit 0
}
New-Item -ItemType Directory -Path $controlDir -Force | Out-Null
$process = Start-Process -FilePath $python -ArgumentList @("-m", "tensorboard.main", "--logdir", $logDir, "--host", "127.0.0.1", "--port", "$Port") `
    -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $controlDir "stdout.log") -RedirectStandardError (Join-Path $controlDir "stderr.log")
$process.Id | Set-Content -LiteralPath $pidPath -Encoding ascii
Write-Host "TensorBoard PID=$($process.Id): http://localhost:$Port"
if (-not $NoBrowser) { Start-Process "http://localhost:$Port" | Out-Null }
