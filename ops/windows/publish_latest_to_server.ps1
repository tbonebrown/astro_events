[CmdletBinding()]
param(
    [switch]$Tess,
    [switch]$Transients
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$server = "tbone@100.81.22.102"
$serverExportRoot = "astro_events_runtime/exports"

function Resolve-LatestTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LinkPath
    )

    $item = Get-Item $LinkPath
    if (-not $item.Target) {
        throw "Latest export link not found or not a symlink: $LinkPath"
    }

    $target = $item.Target
    if ($target -is [System.Array]) {
        return [string]$target[0]
    }

    return [string]$target
}

if (-not $Tess -and -not $Transients) {
    $Tess = $true
    $Transients = $true
}

ssh $server "mkdir -p ~/$serverExportRoot/transients"

if ($Tess) {
    $tessLink = Join-Path $repoRoot "exports\latest"
    if (Test-Path $tessLink) {
        $tessLatest = Resolve-LatestTarget -LinkPath $tessLink
        ssh $server "rm -rf ~/$serverExportRoot/latest"
        scp -r $tessLatest "${server}:$serverExportRoot/latest"
        Write-Output "Published latest TESS export to $server."
    } else {
        Write-Output "Skipping TESS publish because no latest export link exists."
    }
}

if ($Transients) {
    $transientLink = Join-Path $repoRoot "exports\transients\latest"
    if (Test-Path $transientLink) {
        $transientLatest = Resolve-LatestTarget -LinkPath $transientLink
        ssh $server "rm -rf ~/$serverExportRoot/transients/latest"
        scp -r $transientLatest "${server}:$serverExportRoot/transients/latest"
        Write-Output "Published latest transient export to $server."
    } else {
        Write-Output "Skipping transient publish because no latest export link exists."
    }
}
