"""
Screenshot-based scraper using OCR to extract data from images
"""
from playwright.sync_api import sync_playwright
import time
import re
from pathlib import Path

def scrape_with_screenshots(url: str, headless: bool = False):
    """
    Scrape game data by taking screenshots and using OCR
    """
    print("=" * 80)
    print("SCREENSHOT-BASED SCRAPING")
    print("=" * 80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        print(f"\nNavigating to: {url}")
        page.goto(url, wait_until="load", timeout=60000)
        
        print("Waiting for page to load...")
        time.sleep(3)
        
        # Scroll to load content
        print("Scrolling to load content...")
        for i in range(5):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(0.5)
        
        # Click Stats & Insights tab
        print("\nLooking for Stats & Insights tab...")
        try:
            stats_tab = page.locator('text=/Stats.*Insights/i').first
            if stats_tab.is_visible(timeout=5000):
                print("✓ Found Stats & Insights tab, clicking...")
                stats_tab.click()
                print("Waiting 15 seconds for content to load...")
                time.sleep(15)
                
                # Scroll within stats section
                print("Scrolling to load all stats content...")
                for i in range(15):
                    page.evaluate("window.scrollBy(0, 400)")
                    time.sleep(0.5)
                
                # Scroll back to top of stats section
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(1)
            else:
                print("✗ Stats & Insights tab not visible")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Take screenshots of different sections
        screenshots_dir = Path("debug/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        print("\nTaking screenshots...")
        
        # Full page screenshot
        full_screenshot = screenshots_dir / "full_page.png"
        page.screenshot(path=str(full_screenshot), full_page=True)
        print(f"  ✓ Saved full page: {full_screenshot}")
        
        # Viewport screenshot (what's currently visible)
        viewport_screenshot = screenshots_dir / "viewport.png"
        page.screenshot(path=str(viewport_screenshot))
        print(f"  ✓ Saved viewport: {viewport_screenshot}")
        
        # Try to screenshot specific sections if we can find them
        try:
            # Look for the stats panel on the right side
            stats_panel = page.locator('[class*="stats"]').first
            if stats_panel.is_visible(timeout=2000):
                stats_screenshot = screenshots_dir / "stats_panel.png"
                stats_panel.screenshot(path=str(stats_screenshot))
                print(f"  ✓ Saved stats panel: {stats_screenshot}")
        except:
            print("  ✗ Could not find stats panel for screenshot")
        
        # Save HTML for reference
        html_file = screenshots_dir / "page.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"  ✓ Saved HTML: {html_file}")
        
        print("\n" + "=" * 80)
        print("Screenshots saved! Now we can use OCR to extract text.")
        print("=" * 80)
        
        print("\nPress Enter to close browser...")
        input()
        
        browser.close()
        
        return screenshots_dir

if __name__ == "__main__":
    url = "https://www.sportsbet.com.au/betting/basketball-us/nba/los-angeles-lakers-at-boston-celtics-9911701"
    screenshots_dir = scrape_with_screenshots(url, headless=False)
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("\n1. Install OCR library:")
    print("   pip install easyocr")
    print("\n2. Run OCR on screenshots:")
    print("   python ocr_extract.py")
    print("\n" + "=" * 80)
