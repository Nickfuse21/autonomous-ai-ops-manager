param(
    [switch]$RequireFrontend
)

$ErrorActionPreference = "Stop"

function Check-Command {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$InstallHint
    )

    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Host "[MISSING] $Name" -ForegroundColor Red
        Write-Host "  -> $InstallHint" -ForegroundColor Yellow
        return $false
    }

    Write-Host "[OK] $Name -> $($cmd.Source)" -ForegroundColor Green
    return $true
}

Write-Host "Checking runtime prerequisites..." -ForegroundColor Cyan

$ok = $true
$ok = (Check-Command -Name "python" -InstallHint "Install Python 3.11+ and re-open terminal.") -and $ok
$ok = (Check-Command -Name "pip" -InstallHint "Ensure pip is installed with Python and in PATH.") -and $ok

if ($RequireFrontend) {
    $ok = (Check-Command -Name "node" -InstallHint "Install Node.js LTS (includes npm).") -and $ok
    $ok = (Check-Command -Name "npm" -InstallHint "Install Node.js LTS (includes npm).") -and $ok
}

if (-not $ok) {
    Write-Host ""
    Write-Host "Some prerequisites are missing. Install them, then run this script again." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "All required prerequisites are available." -ForegroundColor Green
