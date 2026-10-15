param(
    [int]$TimeoutSeconds = 300,
    [switch]$ForceAfterTimeout
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$activePath = Join-Path $projectRoot "outputs\qlora\control\active_run.json"
if (-not (Test-Path -LiteralPath $activePath)) { throw "No managed QLoRA run was found." }
$active = Get-Content -LiteralPath $activePath -Raw -Encoding utf8 | ConvertFrom-Json
$state = Get-Content -LiteralPath $active.state_path -Raw -Encoding utf8 | ConvertFrom-Json
$workerInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($state.worker_pid)" -ErrorAction SilentlyContinue
$trainingInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($state.training_pid)" -ErrorAction SilentlyContinue
if (-not $trainingInfo) {
    Write-Host "Training process has already exited. Exit code: $($state.exit_code)"
    exit 0
}
if ($trainingInfo.CommandLine -notlike "*vigovbot.training.train*" -or $trainingInfo.CommandLine -notlike "*$($active.run_id)*") {
    if (-not $state.resume_checkpoint -or $trainingInfo.CommandLine -notlike "*$($state.resume_checkpoint)*") {
        throw "PID $($state.training_pid) does not match this QLoRA run; refusing to stop it."
    }
}
if (-not $workerInfo -or $workerInfo.CommandLine -notlike "*run_qlora_worker.ps1*" -or $workerInfo.CommandLine -notlike "*$($active.run_id)*") {
    throw "Worker identity mismatch; refusing to affect another process."
}

$controlDir = Join-Path $state.run_dir "control"
New-Item -ItemType Directory -Path $controlDir -Force | Out-Null
$requestPath = Join-Path $controlDir "stop.requested"
$requestedAt = Get-Date
"requested_at_utc=$([DateTime]::UtcNow.ToString('o'))`nrequested_by_pid=$PID" | Set-Content -LiteralPath $requestPath -Encoding utf8
Write-Host "Graceful stop requested for run $($active.run_id)."

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline -and (Get-Process -Id $state.training_pid -ErrorAction SilentlyContinue)) {
    Start-Sleep -Seconds 2
}
$stillRunning = Get-Process -Id $state.training_pid -ErrorAction SilentlyContinue
if ($stillRunning) {
    if (-not $ForceAfterTimeout) {
        Write-Warning "Timeout reached; process is still running and was not killed. Use -ForceAfterTimeout only if checkpoint loss risk is accepted."
        exit 2
    }
    $verified = Get-CimInstance Win32_Process -Filter "ProcessId = $($state.training_pid)" -ErrorAction SilentlyContinue
    if (-not $verified -or $verified.CommandLine -notlike "*vigovbot.training.train*") { throw "PID identity changed; refusing force-kill." }
    Stop-Process -Id $state.training_pid
    Write-Warning "The verified training PID was force-killed; no new checkpoint is claimed."
    exit 3
}

$newCheckpoint = Get-ChildItem -LiteralPath (Join-Path $state.run_dir "checkpoints") -Directory -Filter "checkpoint-*" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -ge $requestedAt } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$exitCode = if (Test-Path $state.exit_code_file) { (Get-Content $state.exit_code_file -Raw).Trim() } else { "pending" }
if ($newCheckpoint) {
    Write-Host "Process stopped. Verified checkpoint written after request: $($newCheckpoint.FullName). Exit code: $exitCode"
} else {
    Write-Warning "Process stopped, but no new checkpoint was verified after the request. Existing checkpoints remain. Exit code: $exitCode"
}
