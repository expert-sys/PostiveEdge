"""
Cookie Management
=================
Handles cookie storage and rotation for session persistence.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CookieManager:
    """Manages cookies for persistent sessions"""
    
    def __init__(self, cookie_file: Optional[Path] = None):
        """
        Initialize cookie manager.
        
        Args:
            cookie_file: Path to cookie storage file
        """
        self.cookie_file = cookie_file or Path("data/cache/cookies.json")
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
        self.cookies: Dict[str, Dict] = {}
        self._load_cookies()
    
    def _load_cookies(self):
        """Load cookies from file"""
        if self.cookie_file.exists():
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cookies = data.get('cookies', {})
                logger.debug(f"Loaded {len(self.cookies)} cookie sets")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
                self.cookies = {}
    
    def _save_cookies(self):
        """Save cookies to file"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'cookies': self.cookies
            }
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")
    
    def get_cookies(self, domain: str) -> Dict[str, str]:
        """
        Get cookies for a domain.
        
        Args:
            domain: Domain name (e.g., 'databallr.com')
        
        Returns:
            Dict of cookie name: value
        """
        domain_cookies = self.cookies.get(domain, {})
        
        # Filter expired cookies
        valid_cookies = {}
        now = datetime.now()
        
        for name, cookie_data in domain_cookies.items():
            expires = cookie_data.get('expires')
            if expires:
                try:
                    expire_time = datetime.fromisoformat(expires)
                    if expire_time > now:
                        valid_cookies[name] = cookie_data.get('value', '')
                except:
                    valid_cookies[name] = cookie_data.get('value', '')
            else:
                # No expiration - assume valid
                valid_cookies[name] = cookie_data.get('value', '')
        
        return valid_cookies
    
    def set_cookies(self, domain: str, cookies: Dict[str, str], expires: Optional[datetime] = None):
        """
        Store cookies for a domain.
        
        Args:
            domain: Domain name
            cookies: Dict of cookie name: value
            expires: Optional expiration datetime
        """
        if domain not in self.cookies:
            self.cookies[domain] = {}
        
        for name, value in cookies.items():
            self.cookies[domain][name] = {
                'value': value,
                'expires': expires.isoformat() if expires else None,
                'set_at': datetime.now().isoformat()
            }
        
        self._save_cookies()
        logger.debug(f"Saved {len(cookies)} cookies for {domain}")

