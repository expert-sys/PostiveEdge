"""
Extract team insights data - focused approach
"""
from playwright.sync_api import sync_playwright
import time
import json
from pathlib import Path

url = "https://www.sportsbet.com.au/betting/basketball-us/nba/los-angeles-lakers-at-boston-celtics-9911701"

print("=" * 80)
print("TEAM INSIGHTS DATA EXTRACTION")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    # Capture network requests
    api_calls = []
    
    def handle_response(response):
        if 'apigw' in response.url or 'api' in response.url:
            try:
                api_calls.append({
                    'url': response.url,
                    'status': response.status,
                    'method': response.request.method
                })
            except:
                pass
    
    page = context.new_page()
    page.on('response', handle_response)
    
    print(f"\nNavigating to: {url}")
    page.goto(url, wait_until="networkidle", timeout=60000)
    
    print("\nWaiting 3 seconds...")
    time.sleep(3)
    
    print("\nClicking Stats & Insights tab...")
    try:
        stats_tab = page.locator('text=/Stats.*Insights/i').first
        stats_tab.click()
        
        print("Waiting 10 seconds for content to load...")
        time.sleep(10)
        
        # Check for API calls
        print(f"\n📡 Captured {len(api_calls)} API calls")
        for call in api_calls[-10:]:  # Last 10
            print(f"  {call['method']} {call['url'][:100]}")
        
        # Save all API calls
        with open('debug/stats_api_calls.json', 'w') as f:
            json.dump(api_calls, f, indent=2)
        print(f"\n✓ Saved API calls to debug/stats_api_calls.json")
        
        # Try to find team toggles
        print("\n🔍 Looking for team toggle buttons...")
        team_toggles = page.locator('[class*="toggle"], [class*="Toggle"], button').all()
        print(f"  Found {len(team_toggles)} potential toggle elements")
        
        # Look for specific text patterns
        print("\n🔍 Searching for key text patterns...")
        patterns = [
            "Season Results",
            "Head to Head",
            "Last 5",
            "2024",
            "2025",
            "W-L",
            "Points"
        ]
        
        page_text = page.evaluate("() => document.body.innerText")
        for pattern in patterns:
            count = page_text.count(pattern)
            if count > 0:
                print(f"  ✓ Found '{pattern}' ({count} times)")
            else:
                print(f"  ✗ Missing '{pattern}'")
        
        # Try to find and click team toggles
        print("\n🖱️ Attempting to click team toggles...")
        
        # Look for buttons with team names
        away_team = "Lakers"
        home_team = "Celtics"
        
        for team_name in [away_team, home_team]:
            try:
                # Try multiple selector strategies
                selectors = [
                    f'button:has-text("{team_name}")',
                    f'[role="button"]:has-text("{team_name}")',
                    f'div:has-text("{team_name}")[class*="toggle"]',
                ]
                
                for selector in selectors:
                    try:
                        toggle = page.locator(selector).first
                        if toggle.is_visible(timeout=1000):
                            print(f"  Clicking {team_name} toggle...")
                            toggle.click()
                            time.sleep(2)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"  Could not click {team_name} toggle: {e}")
        
        # Scroll to load more content
        print("\n📜 Scrolling to load content...")
        for i in range(10):
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(0.2)
        
        time.sleep(2)
        
        # Extract all visible text
        final_text = page.evaluate("() => document.body.innerText")
        
        # Save to file
        with open('debug/stats_insights_text.txt', 'w', encoding='utf-8') as f:
            f.write(final_text)
        print(f"\n✓ Saved page text to debug/stats_insights_text.txt")
        
        # Take screenshot
        page.screenshot(path='debug/stats_insights_final.png', full_page=True)
        print(f"✓ Saved screenshot to debug/stats_insights_final.png")
        
        # Try to extract structured data
        print("\n📊 Attempting to extract structured data...")
        
        # Look for table-like structures
        tables = page.locator('table').all()
        print(f"  Found {len(tables)} tables")
        
        # Look for list structures
        lists = page.locator('ul, ol').all()
        print(f"  Found {len(lists)} lists")
        
        # Look for divs with data attributes
        data_divs = page.locator('[data-testid], [data-id], [data-key]').all()
        print(f"  Found {len(data_divs)} elements with data attributes")
        
        print("\n" + "=" * 80)
        print("EXTRACTION COMPLETE")
        print("=" * 80)
        print("\nCheck the files:")
        print("  - debug/stats_api_calls.json")
        print("  - debug/stats_insights_text.txt")
        print("  - debug/stats_insights_final.png")
        print("\nPress Enter to close...")
        input()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    browser.close()
