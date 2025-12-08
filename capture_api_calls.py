"""
Automatically capture API calls to find the Stats & Insights endpoint
"""
from playwright.sync_api import sync_playwright
import json
import time

url = "https://www.sportsbet.com.au/betting/basketball-us/nba/los-angeles-lakers-at-boston-celtics-9911701"

print("=" * 80)
print("CAPTURING API CALLS")
print("=" * 80)

captured_requests = []

def handle_response(response):
    """Capture all API responses"""
    try:
        # Only capture API calls (JSON responses)
        if 'api' in response.url.lower() or 'json' in response.headers.get('content-type', '').lower():
            captured_requests.append({
                'url': response.url,
                'status': response.status,
                'content_type': response.headers.get('content-type', ''),
                'method': response.request.method
            })
            print(f"\n📡 API Call: {response.request.method} {response.url[:100]}")
            
            # Try to get the response body
            try:
                if response.status == 200:
                    body = response.text()
                    if len(body) < 500:
                        print(f"   Response: {body[:200]}")
                    else:
                        print(f"   Response size: {len(body)} bytes")
                        # Check if it contains season results data
                        if 'season' in body.lower() or 'head' in body.lower():
                            print("   ⭐ This might contain season/H2H data!")
            except:
                pass
    except Exception as e:
        pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    page = context.new_page()
    
    # Listen to all responses
    page.on("response", handle_response)
    
    print(f"\nNavigating to: {url}")
    page.goto(url, wait_until="load", timeout=60000)
    
    print("\nWaiting for initial page load...")
    time.sleep(3)
    
    print("\nScrolling to load content...")
    for i in range(5):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(0.5)
    
    print("\nLooking for Stats & Insights tab...")
    try:
        stats_tab = page.locator('text=/Stats.*Insights/i').first
        if stats_tab.is_visible(timeout=5000):
            print("✓ Found Stats & Insights tab, clicking...")
            stats_tab.click()
            
            print("\nWaiting 20 seconds for API calls...")
            time.sleep(20)
            
            print("\nScrolling within stats section...")
            for i in range(10):
                page.evaluate("window.scrollBy(0, 500)")
                time.sleep(0.5)
        else:
            print("✗ Stats & Insights tab not visible")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 80)
    print(f"CAPTURED {len(captured_requests)} API CALLS")
    print("=" * 80)
    
    # Save captured requests
    with open("debug/captured_api_calls.json", "w") as f:
        json.dump(captured_requests, f, indent=2)
    print(f"\n✓ Saved to: debug/captured_api_calls.json")
    
    # Show summary
    if captured_requests:
        print("\nAPI Endpoints found:")
        for req in captured_requests:
            print(f"  - {req['url']}")
    
    print("\nPress Enter to close browser...")
    input()
    
    browser.close()
