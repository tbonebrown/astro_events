$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $repoRoot ".env"

if (-not (Test-Path $pythonExe)) {
    throw "Python environment not found at $pythonExe"
}

if (-not (Test-Path $envFile)) {
    throw ".env file not found at $envFile"
}

$tcpClient = New-Object System.Net.Sockets.TcpClient
try {
    $tcpClient.Connect("127.0.0.1", 8000)
    if ($tcpClient.Connected) {
        Write-Output "Astro Events API is already listening on 127.0.0.1:8000."
        return
    }
} catch {
    # Port is not accepting connections yet, so continue with startup.
} finally {
    $tcpClient.Dispose()
}

$arguments = @(
    "-m", "uvicorn",
    "services.api.main:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--proxy-headers",
    "--forwarded-allow-ips=*",
    "--env-file", ".env"
)

Set-Location $repoRoot
& $pythonExe @arguments
