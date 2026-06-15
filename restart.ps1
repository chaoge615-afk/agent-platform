# Agent Platform - Restart Script (PowerShell)
# 设置 UTF-8 编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Agent Platform - Restart" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop existing services
Write-Host "[1/5] Stopping services..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | Stop-Process -Force
    Write-Host "      [OK] Stopped Python processes" -ForegroundColor Green
} else {
    Write-Host "      [-] No running Python processes" -ForegroundColor Gray
}
Write-Host ""

# Step 2: Clear cache
Write-Host "[2/5] Clearing cache..." -ForegroundColor Yellow
$cachePaths = @(
    "src\__pycache__",
    "src\agent\__pycache__"
)
foreach ($path in $cachePaths) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force
        Write-Host "      [OK] Cleared $path" -ForegroundColor Green
    }
}
Write-Host ""

# Step 3: Start server
Write-Host "[3/5] Starting server..." -ForegroundColor Yellow
$process = Start-Process -FilePath "venv\Scripts\python.exe" `
    -ArgumentList "-m", "src.main" `
    -RedirectStandardOutput "server_stdout.log" `
    -RedirectStandardError "server_error.log" `
    -PassThru -NoNewWindow
Write-Host "      [OK] Server starting (PID: $($process.Id))..." -ForegroundColor Green
Write-Host ""

# Step 4: Wait for ready
Write-Host "[4/5] Waiting for server ready..." -ForegroundColor Yellow
$maxAttempts = 15
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ready = $true
            Write-Host "      [OK] Server is ready" -ForegroundColor Green
        }
    } catch {
        Write-Host "      [-] Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    Write-Host "      [FAIL] Server failed to start within 30 seconds" -ForegroundColor Red
    Write-Host "      Check server_stdout.log and server_error.log for details" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Show status
Write-Host "[5/5] Service Status" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8001/health"
    $health | ConvertTo-Json
} catch {
    Write-Host "      [FAIL] Failed to get health status" -ForegroundColor Red
}
Write-Host ""

# Summary
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[OK] Restart complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  - API Docs:    http://localhost:8001/docs"
Write-Host "  - Health:      http://localhost:8001/health"
Write-Host "  - Chat API:    http://localhost:8001/api/chat"
Write-Host ""
Write-Host "Test commands:" -ForegroundColor Yellow
Write-Host "  venv\Scripts\python.exe test_api.py"
Write-Host "  venv\Scripts\python.exe test_multiturn.py"
Write-Host "============================================================" -ForegroundColor Cyan
