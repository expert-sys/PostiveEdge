"""
Helper script to find the API endpoint for Stats & Insights data

INSTRUCTIONS:
1. Run this script with headless=False
2. When the browser opens, open DevTools (F12)
3. Go to the Network tab
4. Click on the Stats & Insights tab
5. Look for API calls (XHR/Fetch filter)
6. Find calls that return JSON with season results or head-to-head data
7. Copy the URL and we can call it directly!
"""
from playwright.sync_api import sync_playwright
import time

url = "https://www.sportsbet.com.au/betting/basketball-us/nba/los-angeles-lakers-at-boston-celtics-9911701"

print("=" * 80)
print("FINDING API ENDPOINT")
print("=" * 80)
print("\nINSTRUCTIONS:")
print("1. Browser will open with DevTools")
print("2. Go to Network tab in DevTools")
print("3. Filter by 'Fetch/XHR'")
print("4. Watch for API calls when Stats & Insights tab is clicked")
print("5. Look for JSON responses with season/H2H data")
print("=" * 80)

input("\nPress Enter to start...")

with sync_playwright() as p:
    # Launch with devtools open
    browser = p.chromium.launch(
        headless=False,
        devtools=True  # This opens DevTools automatically
    )
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    page = context.new_page()
    
    print(f"\nNavigating to: {url}")
    page.goto(url, wait_until="load", timeout=60000)
    
    print("\nPage loaded. Now:")
    print("1. Look at the Network tab in DevTools")
    print("2. Click the Stats & Insights tab")
    print("3. Watch for new network requests")
    print("4. Look for JSON responses")
    
    print("\nBrowser will stay open. Press Enter when done...")
    input()
    
    browser.close()

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("\nOnce you find the API endpoint:")
print("1. Copy the full URL")
print("2. We can call it directly with requests")
print("3. Parse the JSON response")
print("4. Much faster and more reliable than scraping!")
print("=" * 80)
