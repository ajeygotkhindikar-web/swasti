# One-command launcher for SWASTI (Windows PowerShell). Requires Docker Desktop running.
# Run with:  powershell -ExecutionPolicy Bypass -File .\start.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

docker info *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "Docker is not running. Start Docker Desktop, wait until it says 'running', then re-run start.ps1"; exit 1 }

if (-not (Test-Path .env)) {
  Write-Host "Creating .env with fresh secrets and demo data enabled..."
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  $b = New-Object byte[] 32; $rng.GetBytes($b); $jwt = -join ($b | ForEach-Object { $_.ToString('x2') })
  $k = New-Object byte[] 32; $rng.GetBytes($k); $fernet = [Convert]::ToBase64String($k).Replace('+','-').Replace('/','_')
  (Get-Content .env.example) `
    -replace '^JWT_SECRET=.*', "JWT_SECRET=$jwt" `
    -replace '^TRANSCRIPT_ENCRYPTION_KEY=.*', "TRANSCRIPT_ENCRYPTION_KEY=$fernet" `
    -replace '^SEED_FLAGS=.*', 'SEED_FLAGS=--demo' | Set-Content -Encoding ascii .env
}

docker compose up --build -d
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "Waiting for SWASTI to start (first run can take a few minutes)..."
for ($i = 0; $i -lt 120; $i++) {
  try {
    Invoke-WebRequest -UseBasicParsing http://localhost:8080/api/health -TimeoutSec 3 | Out-Null
    Write-Host "SWASTI is running at http://localhost:8080  (demo password: Demo@1234)"
    Start-Process http://localhost:8080
    Write-Host "Logs: docker compose logs -f    Stop: docker compose down"
    exit 0
  } catch { Start-Sleep 5 }
}
Write-Host "SWASTI did not become healthy in time. Recent API logs:"; docker compose logs --tail 40 api; exit 1
