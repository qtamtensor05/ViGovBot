param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][string]$RunId,
    [Parameter(Mandatory = $true)][string]$StatePath,
    [string]$Resume = ""
)

$ErrorActionPreference = "Stop"

function Write-JsonAtomic([string]$Path, [object]$Value) {
    $temp = "$Path.$PID.tmp"
    $Value | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $temp -Encoding utf8
    Move-Item -LiteralPath $temp -Destination $Path -Force
}

Set-Location -LiteralPath $ProjectRoot
$python = Join-Path $ProjectRoot ".venv-qlora\Scripts\python.exe"
$config = Join-Path $ProjectRoot "configs\gpu_rtx5060ti_16gb.yaml"
$state = Get-Content -LiteralPath $StatePath -Raw -Encoding utf8 | ConvertFrom-Json
$stdout = [string]$state.stdout_log
$stderr = [string]$state.stderr_log
$exitPath = [string]$state.exit_code_file
$arguments = @("-u", "-m", "training.train", "--config", $config, "--approve")
if ($Resume) {
    $arguments += @("--resume", $Resume)
} else {
    $arguments += @("--run-id", $RunId)
}

try {
    $env:PYTHONUTF8 = "1"
    $child = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $ProjectRoot `
        -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $state | Add-Member -NotePropertyName training_pid -NotePropertyValue $child.Id -Force
    $state | Add-Member -NotePropertyName worker_pid -NotePropertyValue $PID -Force
    $state | Add-Member -NotePropertyName state -NotePropertyValue "running" -Force
    $state | Add-Member -NotePropertyName training_command -NotePropertyValue ($arguments -join " ") -Force
    Write-JsonAtomic $StatePath $state
    $child.WaitForExit()
    $exitCode = $child.ExitCode
} catch {
    $_ | Out-String | Add-Content -LiteralPath $stderr -Encoding utf8
    $exitCode = 1
}

$exitCode | Set-Content -LiteralPath $exitPath -Encoding ascii
$state = Get-Content -LiteralPath $StatePath -Raw -Encoding utf8 | ConvertFrom-Json
$state | Add-Member -NotePropertyName state -NotePropertyValue "exited" -Force
$state | Add-Member -NotePropertyName exit_code -NotePropertyValue $exitCode -Force
$state | Add-Member -NotePropertyName finished_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString("o")) -Force
Write-JsonAtomic $StatePath $state
exit $exitCode
