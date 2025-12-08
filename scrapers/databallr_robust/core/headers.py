"""
Header Management - Rotating User-Agents and Browser Headers
============================================================
Provides realistic browser headers to avoid detection.
"""

import random
from typing import Dict

# Realistic user agents (updated Chrome/Firefox/Safari)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


def get_random_user_agent() -> str:
    """Get a random user agent from the pool"""
    return random.choice(USER_AGENTS)


def get_browser_headers(referer: str = None, accept: str = None) -> Dict[str, str]:
    """
    Generate realistic browser headers.
    
    Args:
        referer: Optional referer URL
        accept: Optional Accept header (default: text/html)
    
    Returns:
        Dict of headers ready for requests
    """
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': accept or 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none' if not referer else 'same-origin',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    if referer:
        headers['Referer'] = referer
    
    return headers


def get_json_headers(referer: str = None) -> Dict[str, str]:
    """Get headers optimized for JSON API requests"""
    headers = get_browser_headers(referer=referer)
    headers['Accept'] = 'application/json, text/plain, */*'
    headers['Content-Type'] = 'application/json'
    headers['Sec-Fetch-Dest'] = 'empty'
    headers['Sec-Fetch-Mode'] = 'cors'
    return headers

