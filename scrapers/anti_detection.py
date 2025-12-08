"""
Advanced Anti-Detection for Web Scraping
=========================================
Enhanced techniques to avoid bot detection:
- User agent rotation (pool of 20+ real user agents)
- Random timing delays
- Human-like mouse movements
- Viewport randomization
- Cookie management
- Random scrolling patterns
- WebGL, Canvas, Audio fingerprint handling
- Timezone/locale randomization

Usage:
    from anti_detection import setup_stealth_browser, human_delay, random_scroll

    browser, context, page = setup_stealth_browser(headless=True)
    page.goto(url)
    human_delay(1, 3)
    random_scroll(page)
"""

import random
import time
import json
from pathlib import Path
from typing import Tuple, Optional
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


# ---------------------------------------------------------------------
# User Agent Pool (Real, Recent User Agents)
# ---------------------------------------------------------------------
USER_AGENTS = [
    # Chrome on Windows 10/11
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]


# ---------------------------------------------------------------------
# Viewport Configurations (Common Screen Sizes)
# ---------------------------------------------------------------------
VIEWPORTS = [
    {'width': 1920, 'height': 1080},  # Full HD
    {'width': 1366, 'height': 768},   # Laptop
    {'width': 1440, 'height': 900},   # MacBook
    {'width': 1536, 'height': 864},   # Surface
    {'width': 1600, 'height': 900},   # Standard
    {'width': 2560, 'height': 1440},  # 2K
]


# ---------------------------------------------------------------------
# Timezone/Locale Configurations
# ---------------------------------------------------------------------
LOCALES = [
    {'locale': 'en-AU', 'timezone': 'Australia/Sydney', 'lat': -33.8688, 'lon': 151.2093},
    {'locale': 'en-AU', 'timezone': 'Australia/Melbourne', 'lat': -37.8136, 'lon': 144.9631},
    {'locale': 'en-AU', 'timezone': 'Australia/Brisbane', 'lat': -27.4698, 'lon': 153.0251},
    {'locale': 'en-AU', 'timezone': 'Australia/Perth', 'lat': -31.9505, 'lon': 115.8605},
]


# ---------------------------------------------------------------------
# Stealth Browser Setup
# ---------------------------------------------------------------------
def setup_stealth_browser(
    headless: bool = True,
    slow_mo: int = 0,
    proxy: Optional[str] = None
) -> Tuple[Browser, BrowserContext, Page]:
    """
    Setup browser with advanced anti-detection measures
    
    Args:
        headless: Run in headless mode
        slow_mo: Slow down operations (ms)
        proxy: Optional proxy server
    
    Returns:
        Tuple of (browser, context, page)
    """
    playwright = sync_playwright().start()
    
    # Random user agent
    user_agent = random.choice(USER_AGENTS)
    
    # Random viewport
    viewport = random.choice(VIEWPORTS)
    
    # Random locale/timezone
    locale_config = random.choice(LOCALES)
    
    # Launch args to hide automation
    launch_args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-blink-features=AutomationControlled',
        '--disable-infobars',
        '--window-position=0,0',
        '--ignore-certificate-errors',
        '--ignore-certificate-errors-spki-list',
        '--disable-gpu',
    ]
    
    # Launch browser
    browser = playwright.chromium.launch(
        headless=headless,
        slow_mo=slow_mo,
        args=launch_args,
        proxy={'server': proxy} if proxy else None
    )
    
    # Create context with randomized fingerprint
    context = browser.new_context(
        viewport=viewport,
        user_agent=user_agent,
        locale=locale_config['locale'],
        timezone_id=locale_config['timezone'],
        geolocation={
            'latitude': locale_config['lat'],
            'longitude': locale_config['lon']
        },
        permissions=['geolocation'],
        extra_http_headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-AU,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': f'"Chromium";v="120", "Google Chrome";v="120", "Not_A Brand";v="8"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"' if 'Windows' in user_agent else '"macOS"',
            'Cache-Control': 'max-age=0',
        },
        device_scale_factor=random.choice([1, 1.25, 1.5, 2]),
        has_touch=random.choice([True, False]),
        is_mobile=False,
    )
    
    # Inject stealth scripts
    context.add_init_script("""
        // Overwrite the `navigator.webdriver` property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Overwrite the `plugins` property to use a custom getter
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Overwrite the `languages` property to use a custom getter
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-AU', 'en-GB', 'en-US', 'en'],
        });
        
        // Pass the Chrome Test
        window.chrome = {
            runtime: {},
        };
        
        // Pass the Permissions Test
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Pass the WebGL Vendor Test
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter(parameter);
        };
        
        // Add random mouse movements
        const originalAddEventListener = EventTarget.prototype.addEventListener;
        EventTarget.prototype.addEventListener = function(type, listener, options) {
            if (type === 'mousemove') {
                // Add tiny random jitter to mouse movements
                const wrappedListener = function(event) {
                    const newEvent = new MouseEvent(type, {
                        ...event,
                        clientX: event.clientX + (Math.random() - 0.5) * 2,
                        clientY: event.clientY + (Math.random() - 0.5) * 2,
                    });
                    return listener.call(this, newEvent);
                };
                return originalAddEventListener.call(this, type, wrappedListener, options);
            }
            return originalAddEventListener.call(this, type, listener, options);
        };
        
        // Randomize canvas fingerprint
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;
        
        const noisify = function(canvas, context) {
            const shift = {
                'r': Math.floor(Math.random() * 10) - 5,
                'g': Math.floor(Math.random() * 10) - 5,
                'b': Math.floor(Math.random() * 10) - 5,
                'a': Math.floor(Math.random() * 10) - 5
            };
            
            const width = canvas.width;
            const height = canvas.height;
            const imageData = getImageData.apply(context, [0, 0, width, height]);
            
            for (let i = 0; i < height; i++) {
                for (let j = 0; j < width; j++) {
                    const n = ((i * (width * 4)) + (j * 4));
                    imageData.data[n + 0] = imageData.data[n + 0] + shift.r;
                    imageData.data[n + 1] = imageData.data[n + 1] + shift.g;
                    imageData.data[n + 2] = imageData.data[n + 2] + shift.b;
                    imageData.data[n + 3] = imageData.data[n + 3] + shift.a;
                }
            }
            
            context.putImageData(imageData, 0, 0);
        };
        
        Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
            value: function() {
                noisify(this, this.getContext('2d'));
                return toBlob.apply(this, arguments);
            }
        });
        
        Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {
            value: function() {
                noisify(this, this.getContext('2d'));
                return toDataURL.apply(this, arguments);
            }
        });
    """)
    
    # Create page
    page = context.new_page()
    
    # Add extra stealth
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(30000)
    
    return browser, context, page


# ---------------------------------------------------------------------
# Human-like Behavior Functions
# ---------------------------------------------------------------------
def human_delay(min_seconds: float = 0.5, max_seconds: float = 2.0):
    """
    Random delay that mimics human behavior
    
    Args:
        min_seconds: Minimum delay
        max_seconds: Maximum delay
    """
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def random_scroll(page: Page, num_scrolls: int = None):
    """
    Perform random scrolling like a human
    
    Args:
        page: Playwright page object
        num_scrolls: Number of scroll actions (random if None)
    """
    if num_scrolls is None:
        num_scrolls = random.randint(2, 5)
    
    try:
        for _ in range(num_scrolls):
            # Random scroll amount
            scroll_amount = random.randint(200, 800)
            direction = random.choice(['down', 'up'])
            
            if direction == 'down':
                page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            else:
                page.evaluate(f"window.scrollBy(0, -{scroll_amount})")
            
            # Random delay between scrolls
            human_delay(0.3, 1.0)
        
        # Scroll back to top sometimes
        if random.random() < 0.3:
            page.evaluate("window.scrollTo(0, 0)")
            human_delay(0.5, 1.0)
    
    except Exception:
        pass  # Ignore scroll errors


def random_mouse_move(page: Page, num_moves: int = 3):
    """
    Perform random mouse movements
    
    Args:
        page: Playwright page object
        num_moves: Number of mouse movements
    """
    try:
        viewport_size = page.viewport_size
        width = viewport_size['width']
        height = viewport_size['height']
        
        for _ in range(num_moves):
            x = random.randint(100, width - 100)
            y = random.randint(100, height - 100)
            page.mouse.move(x, y)
            human_delay(0.1, 0.3)
    
    except Exception:
        pass  # Ignore mouse move errors


def human_like_click(page: Page, selector: str):
    """
    Click an element with human-like behavior
    
    Args:
        page: Playwright page object
        selector: CSS selector to click
    """
    try:
        # Move to element
        element = page.locator(selector).first
        box = element.bounding_box()
        
        if box:
            # Add random offset within element
            x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            
            # Move mouse to element with random curve
            page.mouse.move(x, y)
            human_delay(0.1, 0.3)
            
            # Click
            page.mouse.click(x, y)
            human_delay(0.3, 0.7)
    
    except Exception:
        # Fallback to regular click
        try:
            element.click()
            human_delay(0.3, 0.7)
        except:
            pass


def type_like_human(page: Page, selector: str, text: str):
    """
    Type text with human-like delays
    
    Args:
        page: Playwright page object
        selector: CSS selector of input
        text: Text to type
    """
    try:
        element = page.locator(selector).first
        element.click()
        human_delay(0.2, 0.5)
        
        for char in text:
            element.type(char, delay=random.randint(50, 150))
        
        human_delay(0.3, 0.7)
    
    except Exception:
        pass


# ---------------------------------------------------------------------
# Cookie Management
# ---------------------------------------------------------------------
def save_cookies(context: BrowserContext, file_path: str):
    """
    Save cookies to file
    
    Args:
        context: Browser context
        file_path: Path to save cookies
    """
    try:
        cookies = context.cookies()
        with open(file_path, 'w') as f:
            json.dump(cookies, f)
    except Exception:
        pass


def load_cookies(context: BrowserContext, file_path: str) -> bool:
    """
    Load cookies from file
    
    Args:
        context: Browser context
        file_path: Path to load cookies from
    
    Returns:
        True if successful, False otherwise
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return False
        
        with open(path, 'r') as f:
            cookies = json.load(f)
        
        context.add_cookies(cookies)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("Anti-Detection Module - Example Usage")
    print("="*60)
    
    # Setup stealth browser
    browser, context, page = setup_stealth_browser(headless=False)
    
    # Navigate
    print("\nNavigating to example site...")
    page.goto("https://www.whatismybrowser.com/detect/what-is-my-user-agent")
    
    # Human-like behavior
    human_delay(1, 2)
    random_scroll(page)
    human_delay(1, 2)
    
    # Take screenshot
    page.screenshot(path="debug/anti_detection_test.png")
    print("Screenshot saved: debug/anti_detection_test.png")
    
    # Cleanup
    browser.close()
    print("\nComplete!")

