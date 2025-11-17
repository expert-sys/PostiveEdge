# Universal Sports Scraper Launcher
Write-Host "Starting Universal Sports Scraper..." -ForegroundColor Cyan
Write-Host ""

try {
    python universal_scraper.py
}
catch {
    Write-Host ""
    Write-Host "Error: Python or required packages not found" -ForegroundColor Red
    Write-Host "Please run: pip install -r scraper_requirements.txt" -ForegroundColor Yellow
    Write-Host "Then run: playwright install chromium" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
}
