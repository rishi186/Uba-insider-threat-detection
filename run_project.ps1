Write-Host "=== Starting UBA Insider Threat Detection System ===" -ForegroundColor Cyan

$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VENV_PYTHON = Join-Path $PROJECT_DIR ".venv\Scripts\python.exe"

# 1. Generate/Update Data (Optional but recommended)
$response = Read-Host "Do you want to regenerate features and retrain models? (y/n)"
if ($response -eq 'y') {
    Write-Host "`n[1/3] Generating Features..." -ForegroundColor Yellow
    & $VENV_PYTHON "$PROJECT_DIR\src\data_pipeline\feature_engineering.py"
    
    Write-Host "`n[2/3] Training Models (This may take a minute)..." -ForegroundColor Yellow
    & $VENV_PYTHON "$PROJECT_DIR\src\models\train_hybrid.py"
}

# 2. Start Backend (Using full path to python -m uvicorn)
Write-Host "`n[3/3] Starting Services..." -ForegroundColor Yellow
Write-Host "Starting Backend API in a new window..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PROJECT_DIR'; & '$VENV_PYTHON' -m uvicorn src.api.main:app --reload --port 8000"

# 3. Start Frontend
Write-Host "Starting Frontend Dashboard in a new window..." -ForegroundColor Green
$WEBSITE_DIR = Join-Path $PROJECT_DIR "website"
if (Test-Path $WEBSITE_DIR) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$WEBSITE_DIR'; npm run dev"
}
else {
    Write-Host "Error: 'website' directory not found." -ForegroundColor Red
}

Write-Host "`nSystem is running!" -ForegroundColor Cyan
Write-Host "Backend: http://localhost:8000/docs"
Write-Host "Frontend: http://localhost:5173"
