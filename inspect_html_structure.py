"""
Inspect the actual HTML structure of the Stats & Insights section
"""
from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup

url = "https://www.sportsbet.com.au/betting/basketball-us/nba/los-angeles-lakers-at-boston-celtics-9911701"

print("=" * 80)
print("INSPECTING HTML STRUCTURE")
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
    time.sleep(3)
    
    print("\nClicking Stats & Insights tab...")
    stats_tab = page.locator('text=/Stats.*Insights/i').first
    stats_tab.click()
    
    print("Waiting 30 seconds for content...")
    time.sleep(30)
    
    # Scroll to make sure everything is loaded
    for i in range(10):
        page.evaluate("window.scrollBy(0, 500)")
        time.sleep(0.5)
    
    print("\nGetting HTML...")
    html = page.content()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Search for text containing "Season Results"
    print("\n" + "=" * 80)
    print("SEARCHING FOR 'Season Results' IN HTML")
    print("=" * 80)
    
    season_elements = soup.find_all(string=lambda text: text and 'Season Results' in text)
    print(f"\nFound {len(season_elements)} elements containing 'Season Results'")
    
    for i, elem in enumerate(season_elements[:3]):
        print(f"\n--- Element {i+1} ---")
        print(f"Text: {elem[:100]}")
        print(f"Parent tag: {elem.parent.name}")
        print(f"Parent class: {elem.parent.get('class', [])}")
        print(f"Parent HTML: {str(elem.parent)[:200]}")
    
    # Search for score patterns
    print("\n" + "=" * 80)
    print("SEARCHING FOR SCORE PATTERNS (123-120)")
    print("=" * 80)
    
    import re
    score_elements = soup.find_all(string=re.compile(r'\d{2,3}-\d{2,3}'))
    print(f"\nFound {len(score_elements)} elements with score patterns")
    
    for i, elem in enumerate(score_elements[:5]):
        print(f"\n--- Score {i+1} ---")
        print(f"Text: {elem}")
        print(f"Parent tag: {elem.parent.name}")
        print(f"Parent class: {elem.parent.get('class', [])}")
    
    # Search for team abbreviations
    print("\n" + "=" * 80)
    print("SEARCHING FOR TEAM ABBREVIATIONS (TOR, PHX, etc.)")
    print("=" * 80)
    
    team_abbrevs = ['TOR', 'PHX', 'NOP', 'DAL', 'LAC']
    for abbrev in team_abbrevs:
        elements = soup.find_all(string=re.compile(abbrev))
        if elements:
            print(f"\n{abbrev}: Found {len(elements)} occurrences")
            elem = elements[0]
            print(f"  Parent: {elem.parent.name}, class: {elem.parent.get('class', [])}")
    
    # Save the HTML for manual inspection
    with open("debug/stats_insights_html.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✓ Saved full HTML to: debug/stats_insights_html.html")
    
    print("\n" + "=" * 80)
    print("Press Enter to close...")
    input()
    
    browser.close()
