param(
    [string]$Resume = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$projectRoot = (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $projectRoot ".venv-qlora\Scripts\python.exe"
$config = Join-Path $projectRoot "configs\gpu_rtx5060ti_16gb.yaml"
$worker = Join-Path $projectRoot "scripts\run_qlora_worker.ps1"
$outputRoot = Join-Path $projectRoot "outputs\qlora"
$controlRoot = Join-Path $outputRoot "control"
$activePath = Join-Path $controlRoot "active_run.json"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python not found: $python" }
if (-not (Test-Path -LiteralPath $config -PathType Leaf)) { throw "Config not found: $config" }

if (Test-Path -LiteralPath $activePath -PathType Leaf) {
    $active = Get-Content -LiteralPath $activePath -Raw -Encoding utf8 | ConvertFrom-Json
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($active.worker_pid)" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -like "*run_qlora_worker.ps1*" -and $process.CommandLine -like "*$($active.run_id)*") {
        throw "A QLoRA worker is already running: run=$($active.run_id), PID=$($active.worker_pid)"
    }
}

$otherTraining = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*training.train*" -and $_.CommandLine -like "*ViGovBot*"
}
if ($otherTraining) {
    $details = ($otherTraining | ForEach-Object { "PID=$($_.ProcessId)" }) -join ", "
    throw "Another ViGovBot training.train process was found ($details). Refusing a second run."
}

$validateArgs = @("-m", "training.control_cli", "--config", $config)
if ($Resume) {
    $Resume = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $Resume))
    $validateArgs += @("--resume", $Resume)
}
$validationText = & $python @validateArgs
if ($LASTEXITCODE -ne 0) { throw "Preflight/data/config/resume validation failed." }
$validation = $validationText | ConvertFrom-Json

if ($Resume) {
    $runDir = [string]$validation.run_dir
    $runId = Split-Path -Leaf $runDir
} else {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $hostName = $env:COMPUTERNAME.ToLowerInvariant()
    $suffix = [Guid]::NewGuid().ToString("N").Substring(0, 8)
    $runId = "qlora-full-$stamp-$hostName-$suffix"
    $runDir = Join-Path $outputRoot $runId
    if (Test-Path -LiteralPath $runDir) { throw "Run directory already exists: $runDir" }
}

$attemptStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$attemptSuffix = [Guid]::NewGuid().ToString("N").Substring(0, 8)
$attemptId = $(if ($Resume) { "resume-$attemptStamp-$attemptSuffix" } else { "start-$attemptStamp-$attemptSuffix" })
$orchestrationDir = Join-Path $controlRoot "runs\$runId\$attemptId"
$statePath = Join-Path $orchestrationDir "process.json"
$stdout = Join-Path $orchestrationDir "stdout.log"
$stderr = Join-Path $orchestrationDir "stderr.log"
$exitPath = Join-Path $orchestrationDir "exit_code.txt"
$state = [ordered]@{
    run_id = $runId
    attempt_id = $attemptId
    run_dir = $runDir
    config = $config
    resume_checkpoint = if ($Resume) { $Resume } else { $null }
    expected_total_steps = [int]$validation.total_steps
    resume_step = [int]$validation.resume_step
    started_at_utc = [DateTime]::UtcNow.ToString("o")
    state = "prepared"
    worker_pid = $null
    training_pid = $null
    stdout_log = $stdout
    stderr_log = $stderr
    exit_code_file = $exitPath
}

if ($DryRun) {
    [pscustomobject]@{
        mode = "DRY_RUN"
        run_id = $runId
        attempt_id = $attemptId
        run_dir = $runDir
        gpu = $validation.gpu
        dataset_records = $validation.dataset_records
        expected_total_steps = $validation.total_steps
        resume_step = $validation.resume_step
        command = "$python -u -m training.train --config $config --approve " + $(if ($Resume) { "--resume $Resume" } else { "--run-id $runId" })
    } | ConvertTo-Json -Depth 8
    exit 0
}

New-Item -ItemType Directory -Path $orchestrationDir -Force | Out-Null
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding utf8
$arguments = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $worker,
    "-ProjectRoot", $projectRoot, "-RunId", $runId, "-StatePath", $statePath
)
if ($Resume) { $arguments += @("-Resume", $Resume) }
$process = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WorkingDirectory $projectRoot `
    -WindowStyle Hidden -PassThru
$latestState = Get-Content -LiteralPath $statePath -Raw -Encoding utf8 | ConvertFrom-Json
$latestState | Add-Member -NotePropertyName worker_pid -NotePropertyValue $process.Id -Force
if (-not $latestState.training_pid) {
    $latestState | Add-Member -NotePropertyName state -NotePropertyValue "starting" -Force
}
$latestState | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding utf8
$active = [ordered]@{ run_id = $runId; worker_pid = $process.Id; state_path = $statePath; run_dir = $runDir }
New-Item -ItemType Directory -Path $controlRoot -Force | Out-Null
$active | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $activePath -Encoding utf8

Write-Host "QLoRA was started in an independent worker."
Write-Host "Run ID: $runId"
Write-Host "Worker PID: $($process.Id)"
Write-Host "Stdout: $stdout"
Write-Host "Stderr: $stderr"
Write-Host "Monitor: .\scripts\status_qlora.ps1"
