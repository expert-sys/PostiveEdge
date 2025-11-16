# ============================================
# VALUE ENGINE - WINDOWS POWERSHELL LAUNCHER
# ============================================
#
# This PowerShell script launches the Value Engine interactive application
# Run from PowerShell (right-click folder, select "Open PowerShell window here")
#
# If you get execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

param(
    [switch]$NoVenv = $false
)

function Write-Header {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "VALUE ENGINE - SPORTS ANALYSIS" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-PythonInstalled {
    try {
        $output = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Python found: $output" -ForegroundColor Green
            return $true
        }
    }
    catch {
        return $false
    }
    return $false
}

function Create-VirtualEnvironment {
    if (Test-Path "venv") {
        Write-Host "✓ Virtual environment exists" -ForegroundColor Green
    }
    else {
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv venv
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Virtual environment created" -ForegroundColor Green
        }
        else {
            Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
            exit 1
        }
    }
}

function Activate-VirtualEnvironment {
    $activateScript = ".\venv\Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
        Write-Host "✓ Virtual environment activated" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Activation script not found" -ForegroundColor Red
        exit 1
    }
}

function Install-Dependencies {
    if (Test-Path "requirements.txt") {
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        pip install -q -r requirements.txt
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Dependencies installed" -ForegroundColor Green
        }
        else {
            Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
            exit 1
        }
    }
}

function Main {
    # Check Python
    if (-not (Test-PythonInstalled)) {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Red
        Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
        Write-Host "============================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please install Python 3.7+ from https://www.python.org/" -ForegroundColor Yellow
        Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Virtual environment setup
    if (-not $NoVenv) {
        Create-VirtualEnvironment
        Activate-VirtualEnvironment
        Install-Dependencies
    }

    # Run application
    Write-Header
    python main.py
}

# Run main function
Main
