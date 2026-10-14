param([string]$RunId = "")

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$outputRoot = Join-Path $projectRoot "outputs\qlora"
$activePath = Join-Path $outputRoot "control\active_run.json"
if (-not $RunId) {
    if (-not (Test-Path -LiteralPath $activePath)) { throw "active_run.json not found. Pass -RunId to inspect an older run." }
    $active = Get-Content -LiteralPath $activePath -Raw -Encoding utf8 | ConvertFrom-Json
    $RunId = [string]$active.run_id
    $statePath = [string]$active.state_path
} else {
    $runControl = Join-Path $outputRoot "control\runs\$RunId"
    $latestState = Get-ChildItem -LiteralPath $runControl -Filter "process.json" -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $statePath = if ($latestState) { $latestState.FullName } else { Join-Path $runControl "process.json" }
}
if (-not (Test-Path -LiteralPath $statePath)) { throw "Process metadata not found for run $RunId" }
$state = Get-Content -LiteralPath $statePath -Raw -Encoding utf8 | ConvertFrom-Json
$worker = if ($state.worker_pid) { Get-Process -Id $state.worker_pid -ErrorAction SilentlyContinue } else { $null }
$training = if ($state.training_pid) { Get-Process -Id $state.training_pid -ErrorAction SilentlyContinue } else { $null }
$livePath = Join-Path ([string]$state.run_dir) "live_status.json"
$live = if (Test-Path -LiteralPath $livePath) { Get-Content -LiteralPath $livePath -Raw -Encoding utf8 | ConvertFrom-Json } else { $null }
$exitCode = if (Test-Path -LiteralPath $state.exit_code_file) { (Get-Content -LiteralPath $state.exit_code_file -Raw).Trim() } else { $null }
$started = [DateTime]::Parse([string]$state.started_at_utc).ToUniversalTime()
$elapsed = if ($live -and $live.elapsed_seconds -ne $null) { [double]$live.elapsed_seconds } else { ([DateTime]::UtcNow - $started).TotalSeconds }
$step = if ($live) { [int]$live.global_step } else { [int]$state.resume_step }
$total = if ($live -and $live.total_steps) { [int]$live.total_steps } else { [int]$state.expected_total_steps }
$eta = if ($live -and $live.eta_seconds -ne $null) { [double]$live.eta_seconds } elseif ($step -gt 0) { $elapsed / $step * ($total - $step) } else { $null }
$gpu = & nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits 2>$null

[pscustomobject]@{
    RunId = $RunId
    WorkerPID = $state.worker_pid
    TrainingPID = $state.training_pid
    ProcessState = if ($training) { "RUNNING" } elseif ($worker) { "WORKER_RUNNING" } else { "EXITED" }
    ExitCode = $exitCode
    GlobalStep = "$step / $total"
    Epoch = if ($live) { $live.epoch } else { $null }
    TrainLoss = if ($live) { $live.loss } else { $null }
    ValidationLoss = if ($live) { $live.eval_loss } else { $null }
    BestValidationLoss = if ($live -and $live.best_validation_loss -ne $null) { $live.best_validation_loss } elseif (Test-Path (Join-Path $state.run_dir "training_metrics.json")) { (Get-Content (Join-Path $state.run_dir "training_metrics.json") -Raw | ConvertFrom-Json).best_validation_loss } else { $null }
    Elapsed = [TimeSpan]::FromSeconds($elapsed).ToString("c")
    ETA = if ($eta -ne $null -and $eta -ge 0) { [TimeSpan]::FromSeconds($eta).ToString("c") } else { "unavailable" }
    GPU = $gpu
    Stdout = $state.stdout_log
    Stderr = $state.stderr_log
} | Format-List
