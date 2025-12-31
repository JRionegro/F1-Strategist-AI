# F1 Strategist AI - PowerShell Launcher
# =======================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  F1 STRATEGIST AI - DASH APPLICATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check and activate virtual environment
$venvPaths = @(".venv\Scripts\Activate.ps1", "venv\Scripts\Activate.ps1")
$venvActivated = $false

foreach ($venvPath in $venvPaths) {
    if (Test-Path $venvPath) {
        Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Green
        & $venvPath
        $venvActivated = $true
        break
    }
}

if (-not $venvActivated) {
    Write-Host "[WARNING] No virtual environment found, using system Python" -ForegroundColor Yellow
}

# Check dependencies
Write-Host "[INFO] Checking dependencies..." -ForegroundColor Green
try {
    python -c "import dash" 2>$null
}
catch {
    Write-Host "[ERROR] Dash not installed. Installing requirements..." -ForegroundColor Red
    pip install -r requirements.txt
}

# Run the application
Write-Host ""
Write-Host "[INFO] Starting F1 Strategist AI Dashboard..." -ForegroundColor Green
Write-Host "[INFO] Open your browser at: " -NoNewline
Write-Host "http://localhost:8501" -ForegroundColor Cyan
Write-Host "[INFO] Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

try {
    python app_dash.py
}
catch {
    Write-Host ""
    Write-Host "[ERROR] Application crashed: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
