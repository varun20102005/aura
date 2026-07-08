Write-Host "Killing any stray servers on port 8000..." -ForegroundColor Yellow
$proc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($proc) { 
    Stop-Process -Id $proc.OwningProcess -Force -ErrorAction SilentlyContinue 
    Write-Host "Killed background process holding port 8000." -ForegroundColor Green
}

Write-Host "Starting AURA services via Docker Compose..." -ForegroundColor Yellow
docker compose up -d --build

Write-Host ""
Write-Host "Services are starting up in the background!" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
