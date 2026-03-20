Write-Host "=== Setting up UBA Insider Threat Detection System ===" -ForegroundColor Cyan

# 1. Install Python Dependencies
Write-Host "`n[1/2] Installing Python Dependencies..." -ForegroundColor Yellow
try {
    pip install pandas numpy scikit-learn xgboost scikit-optimize imbalanced-learn shap torch fastapi uvicorn matplotlib seaborn
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Python dependencies installed successfully." -ForegroundColor Green
    } else {
        Write-Host "Error installing Python dependencies. Please check your Python installation." -ForegroundColor Red
    }
} catch {
    Write-Host "Failed to run pip: $_" -ForegroundColor Red
}

# 2. Install Frontend Dependencies
Write-Host "`n[2/2] Installing Frontend Dependencies..." -ForegroundColor Yellow
if (Test-Path "website") {
    Push-Location "website"
    try {
        npm install
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Frontend dependencies installed successfully." -ForegroundColor Green
        } else {
            Write-Host "Error installing frontend dependencies. Ensure Node.js is installed." -ForegroundColor Red
        }
    } catch {
        Write-Host "Failed to run npm: $_" -ForegroundColor Red
    }
    Pop-Location
} else {
    Write-Host "Error: 'website' directory not found." -ForegroundColor Red
}

Write-Host "`nSetup complete! You can now run 'run_project.ps1' to start the system." -ForegroundColor Cyan
Pause
