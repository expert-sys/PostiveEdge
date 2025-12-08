# PositiveEdge - Comprehensive Launcher (PowerShell)
# Automatically runs full pipeline: Scrapers -> Analysis -> Top Bets

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  PositiveEdge - Comprehensive Betting Analysis" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will run the complete pipeline:" -ForegroundColor Yellow
Write-Host "  1. Sportsbet Scraper (Markets + Insights)" -ForegroundColor White
Write-Host "  2. DataballR Scraper (Player Stats)" -ForegroundColor White
Write-Host "  3. Unified Analysis (Model Projections)" -ForegroundColor White
Write-Host "  4. Display Top Bets (High Confidence)" -ForegroundColor White
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "Warning: Virtual environment not found. Using system Python..." -ForegroundColor Yellow
}

# Run the comprehensive launcher
python launcher_comprehensive.py --auto

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

