# Launch the whole backend on Windows: 4 services behind 1 gateway.
# Each service runs on its own port; the gateway (:8000) is what the frontend hits.
#
#   ./start_all.ps1
#
# If PowerShell blocks the script, run once:
#   powershell -ExecutionPolicy Bypass -File .\start_all.ps1
#
# Ctrl-C stops everything.

$ErrorActionPreference = "Stop"

# backend/ — so `from common...` and `services...` resolve
Set-Location -Path $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot

# Prefer the venv interpreter, fall back to whatever `python` is on PATH.
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$services = @(
    @{ Name = "auth-service";      Module = "services.auth.main:app";      Port = 9001 },
    @{ Name = "jobs-service";      Module = "services.jobs.main:app";      Port = 9002 },
    @{ Name = "screening-service"; Module = "services.screening.main:app"; Port = 9003 },
    @{ Name = "interview-service"; Module = "services.interview.main:app"; Port = 9004 },
    @{ Name = "gateway";           Module = "gateway:app";                 Port = 8000 }
)

$procs = @()
try {
    Write-Host "Starting backend services..."
    foreach ($s in $services) {
        Write-Host ("  -> {0} on :{1}" -f $s.Name, $s.Port)
        $p = Start-Process -FilePath $py `
            -ArgumentList @("-m", "uvicorn", $s.Module, "--port", "$($s.Port)", "--reload") `
            -NoNewWindow -PassThru
        $procs += $p
    }

    Write-Host ""
    Write-Host "Gateway ready at http://localhost:8000  (frontend talks to this)"
    Write-Host "Press Ctrl-C to stop all services."

    # Block until any service exits (or Ctrl-C breaks out to finally).
    Wait-Process -Id ($procs | ForEach-Object { $_.Id })
}
finally {
    Write-Host ""
    Write-Host "Stopping services..."
    foreach ($p in $procs) {
        if ($p -and -not $p.HasExited) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
