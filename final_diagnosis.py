"""
Final diagnosis - let's see exactly what's on the page after clicking Stats & Insights
"""
from playwright.sync_api import sync_playwright
import time
from pathlib import Path

url = "https://www.sportsbet.com.au/betting/basketball-us/nba/los-angeles-lakers-at-boston-celtics-9911701"

print("=" * 80)
print("FINAL DIAGNOSIS")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    page = context.new_page()
    
    print(f"\nNavigating to: {url}")
    page.goto(url, wait_until="networkidle", timeout=60000)
    
    print("\nWaiting 5 seconds...")
    time.sleep(5)
    
    print("\nClicking Stats & Insights tab...")
    try:
        stats_tab = page.locator('text=/Stats.*Insights/i').first
        stats_tab.click()
        
        print("Waiting 30 seconds for content to fully load...")
        time.sleep(30)
        
        # Scroll extensively
        print("Scrolling...")
        for i in range(20):
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(0.3)
        
        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(2)
        
        # Now check what's on the page
        print("\n" + "=" * 80)
        print("CHECKING PAGE CONTENT")
        print("=" * 80)
        
        page_text = page.evaluate("() => document.body.innerText")
        
        # Check for key phrases
        checks = [
            "Season Results",
            "2025/26",
            "Head to Head",
            "Last 5",
            "TOR",
            "PHX",
            "123-120"
        ]
        
        print("\nSearching for key phrases:")
        for phrase in checks:
            if phrase in page_text:
                print(f"  ✓ Found: '{phrase}'")
            else:
                print(f"  ✗ Missing: '{phrase}'")
        
        # Save full page text
        text_file = Path("debug/final_page_text.txt")
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(page_text)
        print(f"\n✓ Saved page text to: {text_file}")
        
        # Take screenshot
        screenshot_file = Path("debug/final_screenshot.png")
        page.screenshot(path=str(screenshot_file), full_page=True)
        print(f"✓ Saved screenshot to: {screenshot_file}")
        
        # Check if there are iframes
        frames = page.frames
        print(f"\n📄 Found {len(frames)} frames on the page")
        if len(frames) > 1:
            print("   ⚠ Content might be in an iframe!")
            for i, frame in enumerate(frames):
                print(f"   Frame {i}: {frame.url[:100]}")
        
        # Try to find the stats panel element
        print("\n🔍 Looking for stats panel elements...")
        selectors_to_try = [
            '[class*="stats"]',
            '[class*="Stats"]',
            '[class*="insight"]',
            '[class*="Insight"]',
            '[data-testid*="stats"]',
            '[id*="stats"]',
        ]
        
        for selector in selectors_to_try:
            try:
                elements = page.locator(selector).all()
                if elements:
                    print(f"  ✓ Found {len(elements)} elements with selector: {selector}")
            except:
                pass
        
        print("\n" + "=" * 80)
        print("DIAGNOSIS COMPLETE")
        print("=" * 80)
        print("\nCheck the files:")
        print(f"  - {text_file}")
        print(f"  - {screenshot_file}")
        print("\nPress Enter to close...")
        input()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    browser.close()
