"""
Diagnostic script to understand Season Results and H2H extraction issues
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re

TEST_URL = "https://www.sportsbet.com.au/betting/basketball-us/nba/los-angeles-lakers-at-boston-celtics-9911701"

print("="  * 80)
print("DIAGNOSING SEASON RESULTS & HEAD-TO-HEAD EXTRACTION")
print("=" * 80)
print()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Visible browser
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    page = context.new_page()

    print(f"Loading: {TEST_URL}")
    page.goto(TEST_URL, wait_until="load", timeout=60000)
    time.sleep(3)

    # Scroll
    print("Scrolling...")
    for i in range(5):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(0.3)

    # Click Stats & Insights tab
    print("\nLooking for Stats & Insights tab...")
    try:
        stats_tab = page.locator('text=/Stats.*Insights/i').first
        if stats_tab.is_visible(timeout=5000):
            print("✓ Found and clicking Stats & Insights tab")
            stats_tab.click()
            time.sleep(10)  # Wait longer

            # Get all visible text
            all_text = page.evaluate("() => document.body.innerText")

            # Check for season results
            if "Season Results" in all_text or "season results" in all_text.lower():
                print("✓ 'Season Results' found in page text")
            else:
                print("✗ 'Season Results' NOT in page text")

            # Check for H2H
            if "Head to Head" in all_text or "head-to-head" in all_text.lower():
                print("✓ 'Head to Head' found in page text")
            else:
                print("✗ 'Head to Head' NOT in page text")

            # Save HTML for analysis
            html = page.content()
            with open('debug/diagnosis_full_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("\n✓ Saved HTML to: debug/diagnosis_full_page.html")

            # Take screenshot
            page.screenshot(path='debug/diagnosis_full_page.png', full_page=True)
            print("✓ Saved screenshot to: debug/diagnosis_full_page.png")

            # Try to find season results elements
            print("\nSearching for season results elements...")
            soup = BeautifulSoup(html, 'html.parser')

            # Search for various patterns
            patterns = [
                ("2025/26", "Season year"),
                ("2024/25", "Previous season"),
                ("W L", "Win/Loss indicator"),
                ("Season Results", "Direct match"),
                ("Head to Head", "H2H direct match"),
                ("Last 5", "Recent games"),
            ]

            for pattern, desc in patterns:
                elements = soup.find_all(string=lambda t: t and pattern in t)
                if elements:
                    print(f"  ✓ Found '{pattern}' ({desc}): {len(elements)} occurrences")
                    for elem in elements[:1]:
                        parent = elem.find_parent()
                        if parent:
                            print(f"    Tag: <{parent.name}> Classes: {parent.get('class')}")
                else:
                    print(f"  ✗ '{pattern}' ({desc}): Not found")

            # Look for buttons/tabs
            print("\nSearching for interactive elements...")
            buttons = page.locator('button').all()
            print(f"  Total buttons on page: {len(buttons)}")

            # Check for team name buttons
            team_buttons = page.locator('button:has-text("Lakers"), button:has-text("Celtics")').all()
            print(f"  Team toggle buttons: {len(team_buttons)}")

            # Check for More buttons
            more_buttons = page.locator('button:has-text("More")').all()
            print(f"  'More' buttons: {len(more_buttons)}")

            print("\nWaiting 30 seconds for manual inspection...")
            print("(Check the browser window to see what's displayed)")
            time.sleep(30)

        else:
            print("✗ Stats & Insights tab not visible")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        browser.close()

print("\n" + "=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)
print("\nCheck these files:")
print("  - debug/diagnosis_full_page.html")
print("  - debug/diagnosis_full_page.png")
