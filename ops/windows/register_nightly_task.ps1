$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$nightlyScript = Join-Path $repoRoot "ops\windows\run_nightly_publish.ps1"

if (-not (Test-Path $nightlyScript)) {
    throw "Missing nightly publish script at $nightlyScript"
}

$taskName = "Astro Events Nightly Publish"
$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$nightlyScript`""

schtasks /Create /TN $taskName /SC DAILY /ST 03:00 /TR $taskCommand /F | Out-Null
Write-Output "Registered scheduled task '$taskName' for 3:00 AM."
