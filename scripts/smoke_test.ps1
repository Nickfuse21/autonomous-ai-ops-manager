param(
    [switch]$IncludeFrontend
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$venvDir = Join-Path $backendDir ".venv"
$pythonExe = Join-Path $venvDir "Scripts/python.exe"

Write-Host "Step 1/5: Checking prerequisites..." -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "check_prereqs.ps1") -RequireFrontend:$IncludeFrontend

Write-Host "Step 2/5: Preparing backend virtual environment..." -ForegroundColor Cyan
if (-not (Test-Path $pythonExe)) {
    Push-Location $backendDir
    python -m venv .venv
    Pop-Location
}

Write-Host "Step 3/5: Installing backend dependencies..." -ForegroundColor Cyan
Push-Location $backendDir
& $pythonExe -m pip install -r requirements.txt

Write-Host "Step 4/5: Running backend tests..." -ForegroundColor Cyan
& $pythonExe -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Backend tests failed."
}

Write-Host "Step 5/5: Running end-to-end demo cycle..." -ForegroundColor Cyan
& $pythonExe scripts/run_demo.py
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Demo cycle failed."
}
Pop-Location

if ($IncludeFrontend) {
    $frontendDir = Join-Path $projectRoot "frontend"
    Write-Host "Frontend verification: install and build..." -ForegroundColor Cyan
    Push-Location $frontendDir
    npm install
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "Frontend build failed."
    }
    Pop-Location
}

Write-Host ""
Write-Host "Smoke test completed successfully." -ForegroundColor Green
