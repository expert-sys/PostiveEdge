"""
Human-Like Scraper - Avoid Detection
====================================

Mimics human browsing behavior to avoid IP bans:
- Random delays between actions
- Mouse movements and scrolling
- Multiple user agents
- Realistic browsing patterns
"""

from playwright.sync_api import sync_playwright
import time
import random
import json

def human_like_browse():
    """Browse like a human to avoid detection"""
    
    print("=" * 80)
    print("🤖➡️👤 HUMAN-LIKE BROWSING TEST")
    print("=" * 80)
    print("Testing if human-like behavior avoids detection...")
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Show browser to appear more human
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--no-first-run',
                '--disable-default-apps'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},  # Common resolution
            user_agent=random.choice(user_agents),
            locale='en-AU',  # Australian locale
            timezone_id='Australia/Sydney'
        )
        
        # Add realistic headers
        context.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        page = context.new_page()
        
        try:
            print("🌐 Navigating to Sportsbet homepage first (like a human)...")
            page.goto("https://www.sportsbet.com.au", wait_until="load", timeout=30000)
            
            # Human-like delay
            delay = random.uniform(2, 5)
            print(f"⏱️ Waiting {delay:.1f}s (human-like pause)...")
            time.sleep(delay)
            
            # Scroll a bit (humans do this)
            print("📜 Scrolling page (human behavior)...")
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(random.uniform(1, 2))
            page.evaluate("window.scrollBy(0, -150)")
            time.sleep(random.uniform(1, 2))
            
            print("🏀 Navigating to NBA section...")
            page.goto("https://www.sportsbet.com.au/betting/basketball-us/nba", 
                     wait_until="load", timeout=30000)
            
            # Another human-like delay
            delay = random.uniform(3, 6)
            print(f"⏱️ Waiting {delay:.1f}s for page to load...")
            time.sleep(delay)
            
            # Check if we can see the page content
            page_title = page.title()
            print(f"📄 Page title: {page_title}")
            
            # Look for NBA games
            game_links = page.locator('a[href*="/betting/basketball-us/nba/"]').all()
            print(f"🎯 Found {len(game_links)} potential NBA game links")
            
            if len(game_links) > 0:
                print("✅ SUCCESS: Can access NBA page and find games")
                print("The issue might be with aggressive scraping, not access")
                
                # Get a few game URLs
                game_urls = []
                for link in game_links[:3]:
                    try:
                        href = link.get_attribute('href')
                        if href and 'nba' in href:
                            game_urls.append(href)
                    except:
                        pass
                
                print(f"📋 Sample game URLs found: {len(game_urls)}")
                for i, url in enumerate(game_urls, 1):
                    print(f"  {i}. {url}")
                
                return True, game_urls
            else:
                print("❌ FAILED: No NBA games found")
                print("This suggests IP blocking or page structure changes")
                
                # Save page for debugging
                page_content = page.content()
                with open('debug_page_content.html', 'w', encoding='utf-8') as f:
                    f.write(page_content)
                print("💾 Saved page content to debug_page_content.html")
                
                return False, []
                
        except Exception as e:
            print(f"❌ Error during human-like browsing: {e}")
            return False, []
        
        finally:
            browser.close()

def test_single_game_access(game_url):
    """Test accessing a single game page with human-like behavior"""
    
    print(f"\n🎮 Testing single game access: {game_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        try:
            print("🌐 Accessing game page...")
            page.goto(game_url, wait_until="load", timeout=30000)
            
            # Human delay
            time.sleep(random.uniform(3, 5))
            
            # Look for key elements
            title = page.title()
            print(f"📄 Game page title: {title}")
            
            # Check for betting markets
            markets = page.locator('[class*="market"], [class*="Market"]').all()
            print(f"💰 Found {len(markets)} potential betting markets")
            
            if len(markets) > 0:
                print("✅ Can access individual game pages")
                return True
            else:
                print("⚠️ Game page accessible but no markets found")
                return False
                
        except Exception as e:
            print(f"❌ Error accessing game page: {e}")
            return False
        
        finally:
            browser.close()

if __name__ == "__main__":
    print("Testing human-like browsing to avoid IP bans...")
    
    # Test 1: Human-like browsing
    success, game_urls = human_like_browse()
    
    if success and game_urls:
        print(f"\n✅ Human-like browsing successful!")
        
        # Test 2: Try accessing one game page
        test_url = game_urls[0] if game_urls else None
        if test_url:
            game_success = test_single_game_access(test_url)
            
            if game_success:
                print("\n🎉 SOLUTION FOUND!")
                print("Human-like browsing with delays works!")
            else:
                print("\n⚠️ Can access overview but not game pages")
        
    else:
        print("\n❌ Even human-like browsing failed")
        print("Your IP might already be banned")
    
    print("\n" + "=" * 80)
    print("🛡️ ANTI-BAN RECOMMENDATIONS:")
    print("=" * 80)
    print("1. 🐌 Use 30-60 second delays between games")
    print("2. 🎭 Rotate user agents for each session")
    print("3. 🏠 Start from homepage, then navigate (human pattern)")
    print("4. 📜 Add random scrolling and mouse movements")
    print("5. 🔄 Use new browser session for each run")
    print("6. ⏰ Wait 15+ minutes between pipeline runs")
    print("7. 📊 Limit to 1-2 games per session maximum")
    print("8. 🌐 Consider VPN if IP is already banned")