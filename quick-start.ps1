# Quick Start - Simplified 6 Options

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   PositiveEdge - Quick Start" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Run Complete Analysis"
Write-Host "  2. Scrape Data"
Write-Host "  3. Value Analysis"
Write-Host "  4. View Results"
Write-Host "  5. Run Tests"
Write-Host "  6. Exit"
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan

$choice = Read-Host "Select (1-6)"

switch ($choice) {
    "1" { python launcher.py --run 1 }
    "2" { python launcher.py --run 2 }
    "3" { python launcher.py --run 3 }
    "4" { python launcher.py --run 4 }
    "5" { python launcher.py --run 5 }
    "6" { exit }
    default {
        Write-Host "[ERROR] Invalid choice" -ForegroundColor Red
        pause
    }
}
