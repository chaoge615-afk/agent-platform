# Agent Platform - Stop Script (PowerShell)
Write-Host "Stopping Agent Platform services..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | Stop-Process -Force
    Write-Host "✓ Stopped" -ForegroundColor Green
} else {
    Write-Host "- No running services" -ForegroundColor Gray
}
