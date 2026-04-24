$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$startScript = Join-Path $repoRoot "ops\windows\start_api.ps1"

if (-not (Test-Path $startScript)) {
    throw "Missing startup script at $startScript"
}

$taskName = "Astro Events API"
$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$startScript`""

schtasks /Create /TN $taskName /SC ONLOGON /TR $taskCommand /F | Out-Null
Write-Output "Registered scheduled task '$taskName'."
