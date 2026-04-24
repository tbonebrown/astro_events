$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$pythonDir = Join-Path $repoRoot ".venv\Scripts"

if (-not (Test-Path (Join-Path $pythonDir "astro-tess-nightly.exe"))) {
    throw "Astro Events virtual environment is missing under $pythonDir"
}

Set-Location $repoRoot

& (Join-Path $pythonDir "astro-tess-nightly.exe") --synthetic --limit 12 --export-root (Join-Path $repoRoot "exports")
& (Join-Path $pythonDir "astro-api-ingest.exe") --export-dir (Join-Path $repoRoot "exports\latest")
& (Join-Path $pythonDir "astro-transients-nightly.exe") --synthetic --limit 12 --export-root (Join-Path $repoRoot "exports")
& (Join-Path $pythonDir "astro-api-ingest-transients.exe") --export-dir (Join-Path $repoRoot "exports\transients\latest")
