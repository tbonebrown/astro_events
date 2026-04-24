$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$pythonDir = Join-Path $repoRoot ".venv\Scripts"
$exportRoot = Join-Path $repoRoot "exports"
$logDir = Join-Path $repoRoot "var\logs"
$logPath = Join-Path $logDir "nightly_publish.log"
$server = "tbone@100.81.22.102"
$defaultTessTarget = Join-Path $repoRoot "data\tic_targets.csv"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $envPath = Join-Path $repoRoot ".env"
    if (-not (Test-Path $envPath)) {
        return $null
    }

    $line = Get-Content $envPath | Where-Object { $_ -match "^${Name}=" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    return ($line -split "=", 2)[1].Trim()
}

function Invoke-ServerIngest {
    param(
        [bool]$RunTess,
        [bool]$RunTransients
    )

    if ($RunTess) {
        ssh $server "systemctl --user start astro-events-ingest.service"
    }

    if ($RunTransients) {
        ssh $server "systemctl --user start astro-events-transients.service"
    }
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Start-Transcript -Path $logPath -Append | Out-Null

try {
    Set-Location $repoRoot

    $tessTargetFile = Get-DotEnvValue -Name "TESS_TARGET_FILE"
    if ([string]::IsNullOrWhiteSpace($tessTargetFile)) {
        $tessTargetFile = $defaultTessTarget
    }

    try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDir "refresh_tess_targets.ps1")
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "TESS target refresh failed with exit code $LASTEXITCODE"
        }
    } catch {
        Write-Warning "TESS target refresh failed: $($_.Exception.Message)"
    }

    $ranTess = $false
    $ranTransients = $false

    try {
        Invoke-CheckedCommand -Description "Transient export" -Command {
            & (Join-Path $pythonDir "astro-transients-nightly.exe") --limit 100 --export-root $exportRoot
        }
        Invoke-CheckedCommand -Description "Transient ingest" -Command {
            & (Join-Path $pythonDir "astro-api-ingest-transients.exe") --export-dir (Join-Path $exportRoot "transients\latest")
        }
        Invoke-CheckedCommand -Description "Transient publish" -Command {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDir "publish_latest_to_server.ps1") -Transients
        }
        $ranTransients = $true
    } catch {
        Write-Warning "Transient nightly flow failed: $($_.Exception.Message)"
    }

    if (Test-Path $tessTargetFile) {
        try {
            Invoke-CheckedCommand -Description "TESS export" -Command {
                & (Join-Path $pythonDir "astro-tess-nightly.exe") --limit 50 --export-root $exportRoot --tic-target-file $tessTargetFile
            }
            Invoke-CheckedCommand -Description "TESS ingest" -Command {
                & (Join-Path $pythonDir "astro-api-ingest.exe") --export-dir (Join-Path $exportRoot "latest")
            }
            Invoke-CheckedCommand -Description "TESS publish" -Command {
                & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDir "publish_latest_to_server.ps1") -Tess
            }
            $ranTess = $true
        } catch {
            Write-Warning "TESS nightly flow failed: $($_.Exception.Message)"
        }
    } else {
        Write-Output "Skipping TESS nightly run because no target file was found at $tessTargetFile"
    }

    Invoke-ServerIngest -RunTess:$ranTess -RunTransients:$ranTransients
} finally {
    Stop-Transcript | Out-Null
}
