$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$defaultDestination = Join-Path $repoRoot "data\tic_targets.csv"
$envPath = Join-Path $repoRoot ".env"

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Test-Path $envPath)) {
        return $null
    }

    $line = Get-Content $envPath | Where-Object { $_ -match "^${Name}=" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    return ($line -split "=", 2)[1].Trim()
}

$sourceUrl = Get-DotEnvValue -Name "TESS_TARGET_URL"
$serverSourcePath = Get-DotEnvValue -Name "TESS_TARGET_SERVER_PATH"
$destinationPath = Get-DotEnvValue -Name "TESS_TARGET_FILE"

if ([string]::IsNullOrWhiteSpace($destinationPath)) {
    $destinationPath = $defaultDestination
}

if ([string]::IsNullOrWhiteSpace($sourceUrl) -and [string]::IsNullOrWhiteSpace($serverSourcePath)) {
    Write-Output "Skipping TESS target refresh because neither TESS_TARGET_URL nor TESS_TARGET_SERVER_PATH is configured."
    exit 0
}

$destinationDir = Split-Path -Parent $destinationPath
$tempPath = "$destinationPath.download"

New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null

if (-not [string]::IsNullOrWhiteSpace($serverSourcePath)) {
    & scp $serverSourcePath $tempPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to copy TESS target file from $serverSourcePath"
    }
    Write-Output "Downloaded TESS targets from server path $serverSourcePath"
} else {
    Invoke-WebRequest -Uri $sourceUrl -OutFile $tempPath
    Write-Output "Downloaded TESS targets from URL $sourceUrl"
}

$rows = Import-Csv $tempPath
if ($rows.Count -eq 0) {
    Remove-Item $tempPath -Force
    throw "Downloaded TESS target file is empty."
}

$firstRow = $rows | Select-Object -First 1
if (-not ($firstRow.PSObject.Properties.Name -contains "tic_id")) {
    Remove-Item $tempPath -Force
    throw "Downloaded TESS target file must contain a 'tic_id' column."
}

Move-Item -Force $tempPath $destinationPath
Write-Output "Refreshed TESS targets at $destinationPath"
