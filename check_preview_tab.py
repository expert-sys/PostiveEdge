"""
Check if team insights data is in the Preview tab instead
"""
from playwright.sync_api import sync_playwright
import time

url = "https://www.sportsbet.com.au/betting/basketball-us/nba/los-angeles-lakers-at-boston-celtics-9911701"

print("=" * 80)
print("CHECKING PREVIEW TAB FOR TEAM INSIGHTS")
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
    
    print("\nWaiting 3 seconds...")
    time.sleep(3)
    
    # Check what tabs are available
    print("\n🔍 Looking for available tabs...")
    tabs = page.locator('[role="tab"], button[class*="tab"], a[class*="tab"]').all()
    print(f"  Found {len(tabs)} potential tabs")
    
    for i, tab in enumerate(tabs[:10]):  # First 10
        try:
            text = tab.inner_text(timeout=500)
            print(f"  Tab {i}: {text}")
        except:
            pass
    
    # Try clicking Preview tab
    print("\n🖱️ Attempting to click Preview tab...")
    try:
        preview_tab = page.locator('text=/Preview/i').first
        preview_tab.click()
        
        print("Waiting 5 seconds for content to load...")
        time.sleep(5)
        
        # Scroll to load content
        for i in range(10):
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(0.2)
        
        time.sleep(2)
        
        # Check for key phrases
        page_text = page.evaluate("() => document.body.innerText")
        
        patterns = [
            "Season Results",
            "Head to Head",
            "2024/25",
            "2025/26",
            "Last 5",
            "Form",
            "Recent Games"
        ]
        
        print("\n🔍 Searching for key text patterns in Preview tab...")
        for pattern in patterns:
            if pattern in page_text:
                print(f"  ✓ Found: '{pattern}'")
            else:
                print(f"  ✗ Missing: '{pattern}'")
        
        # Save text
        with open('debug/preview_tab_text.txt', 'w', encoding='utf-8') as f:
            f.write(page_text)
        print(f"\n✓ Saved page text to debug/preview_tab_text.txt")
        
        # Take screenshot
        page.screenshot(path='debug/preview_tab.png', full_page=True)
        print(f"✓ Saved screenshot to debug/preview_tab.png")
        
    except Exception as e:
        print(f"  Could not access Preview tab: {e}")
    
    # Try Stats & Insights tab again with more detail
    print("\n🖱️ Attempting to click Stats & Insights tab...")
    try:
        stats_tab = page.locator('text=/Stats.*Insights/i').first
        stats_tab.click()
        
        print("Waiting 5 seconds for content to load...")
        time.sleep(5)
        
        # Scroll extensively
        for i in range(15):
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(0.3)
        
        time.sleep(3)
        
        # Check for key phrases
        page_text = page.evaluate("() => document.body.innerText")
        
        print("\n🔍 Searching for key text patterns in Stats & Insights tab...")
        for pattern in patterns:
            if pattern in page_text:
                print(f"  ✓ Found: '{pattern}'")
                # Show context
                idx = page_text.find(pattern)
                context = page_text[max(0, idx-50):min(len(page_text), idx+100)]
                print(f"     Context: ...{context}...")
            else:
                print(f"  ✗ Missing: '{pattern}'")
        
        # Save text
        with open('debug/stats_insights_detailed.txt', 'w', encoding='utf-8') as f:
            f.write(page_text)
        print(f"\n✓ Saved page text to debug/stats_insights_detailed.txt")
        
        # Take screenshot
        page.screenshot(path='debug/stats_insights_detailed.png', full_page=True)
        print(f"✓ Saved screenshot to debug/stats_insights_detailed.png")
        
    except Exception as e:
        print(f"  Could not access Stats & Insights tab: {e}")
    
    print("\n" + "=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)
    print("\nPress Enter to close...")
    input()
    
    browser.close()
