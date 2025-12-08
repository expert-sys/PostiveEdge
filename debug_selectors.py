"""
Debug script to find the correct selectors for Season Results and Head to Head
"""
from playwright.sync_api import sync_playwright
import time

url = "https://www.sportsbet.com.au/betting/basketball-us/nba/los-angeles-lakers-at-boston-celtics-9911701"

print("=" * 80)
print("DEBUGGING SELECTORS")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    page = context.new_page()
    
    print(f"\nNavigating to: {url}")
    page.goto(url, wait_until="load", timeout=60000)
    
    print("\nWaiting for page to load...")
    time.sleep(3)
    
    # First scroll down to load content
    print("\nScrolling to load content...")
    for i in range(5):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(0.5)
    
    print("\nLooking for Stats & Insights tab...")
    try:
        # Try multiple selectors for the tab
        tab_selectors = [
            'text=/Stats.*Insights/i',
            'button:has-text("Stats")',
            '[role="tab"]:has-text("Stats")',
            'text="Stats & Insights"',
        ]
        
        clicked = False
        for selector in tab_selectors:
            try:
                tab = page.locator(selector).first
                if tab.is_visible(timeout=2000):
                    print(f"✓ Found tab with selector: {selector}")
                    tab.click()
                    clicked = True
                    break
            except:
                continue
        
        if clicked:
            print("Waiting 15 seconds for content to load...")
            time.sleep(15)
            
            # Try scrolling within the stats section
            print("Scrolling within stats section...")
            for i in range(10):
                page.evaluate("window.scrollBy(0, 500)")
                time.sleep(0.5)
        else:
            print("✗ Stats & Insights tab not found with any selector")
    except Exception as e:
        print(f"✗ Error clicking Stats & Insights: {e}")
    
    print("\n" + "=" * 80)
    print("TESTING SELECTORS")
    print("=" * 80)
    
    # Test different selectors for Season Results
    print("\n1. Testing Season Results selectors:")
    season_selectors = [
        'text="2025/26 Season Results"',
        'text=/Season Results/i',
        'text=/2025.*Season Results/i',
        ':text("Season Results")',
        'h2:has-text("Season Results")',
        'h3:has-text("Season Results")',
        'h4:has-text("Season Results")',
        'div:has-text("Season Results")',
        '[class*="season"]',
        '[class*="Season"]',
    ]
    
    for selector in season_selectors:
        try:
            elements = page.locator(selector).all()
            if elements:
                print(f"  ✓ {selector}: Found {len(elements)} element(s)")
                if len(elements) > 0:
                    text = elements[0].text_content()[:100]
                    print(f"    Text: {text}")
            else:
                print(f"  ✗ {selector}: Not found")
        except Exception as e:
            print(f"  ✗ {selector}: Error - {str(e)[:50]}")
    
    # Test different selectors for Head to Head
    print("\n2. Testing Head to Head selectors:")
    h2h_selectors = [
        'text="Last 5 Head to Head"',
        'text=/Head to Head/i',
        'text=/Last.*Head to Head/i',
        ':text("Head to Head")',
        'h2:has-text("Head to Head")',
        'h3:has-text("Head to Head")',
        'h4:has-text("Head to Head")',
        'div:has-text("Head to Head")',
    ]
    
    for selector in h2h_selectors:
        try:
            elements = page.locator(selector).all()
            if elements:
                print(f"  ✓ {selector}: Found {len(elements)} element(s)")
                if len(elements) > 0:
                    text = elements[0].text_content()[:100]
                    print(f"    Text: {text}")
            else:
                print(f"  ✗ {selector}: Not found")
        except Exception as e:
            print(f"  ✗ {selector}: Error - {str(e)[:50]}")
    
    # Check if content is in the page text
    print("\n3. Checking page text content:")
    page_text = page.evaluate("() => document.body.innerText")
    
    if "Season Results" in page_text:
        print("  ✓ 'Season Results' found in page text")
    else:
        print("  ✗ 'Season Results' NOT in page text")
    
    if "Head to Head" in page_text:
        print("  ✓ 'Head to Head' found in page text")
    else:
        print("  ✗ 'Head to Head' NOT in page text")
    
    if "2025/26" in page_text:
        print("  ✓ '2025/26' found in page text")
    else:
        print("  ✗ '2025/26' NOT in page text")
    
    # Save page content for inspection
    with open("debug/page_content.txt", "w", encoding="utf-8") as f:
        f.write(page_text)
    print("\n  ✓ Saved page text to: debug/page_content.txt")
    
    # Save screenshot
    page.screenshot(path="debug/selector_debug.png")
    print("  ✓ Saved screenshot to: debug/selector_debug.png")
    
    print("\n" + "=" * 80)
    print("Press Enter to close browser...")
    input()
    
    browser.close()
