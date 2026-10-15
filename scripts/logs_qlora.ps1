param(
    [string]$RunId = "",
    [int]$Lines = 50,
    [switch]$Follow
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$controlRoot = Join-Path $projectRoot "outputs\qlora\control"
$activePath = Join-Path $controlRoot "active_run.json"
if (-not $RunId) {
    if (-not (Test-Path -LiteralPath $activePath -PathType Leaf)) { throw "No active run metadata found." }
    $active = Get-Content -LiteralPath $activePath -Raw -Encoding utf8 | ConvertFrom-Json
    $statePath = [string]$active.state_path
} else {
    $candidate = Get-ChildItem -LiteralPath (Join-Path $controlRoot "runs\$RunId") -Filter process.json -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $candidate) { throw "Process metadata not found for run $RunId" }
    $statePath = $candidate.FullName
}
$state = Get-Content -LiteralPath $statePath -Raw -Encoding utf8 | ConvertFrom-Json
$paths = @($state.stdout_log, $state.stderr_log) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }
if (-not $paths) { throw "No log file is available for this run yet." }
foreach ($path in $paths) {
    Write-Host "=== $path ==="
    if ($Follow) { Get-Content -LiteralPath $path -Tail $Lines -Wait }
    else { Get-Content -LiteralPath $path -Tail $Lines }
}
