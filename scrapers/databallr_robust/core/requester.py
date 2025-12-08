"""
Robust Request Handler
======================
Handles all HTTP requests with retries, backoff, headers, and error handling.
"""

import time
import random
import logging
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
import json

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import requests

from .headers import get_browser_headers, get_json_headers, get_random_user_agent
from .backoff import RetryConfig, retry_request, calculate_backoff_delay, is_retryable_error

logger = logging.getLogger(__name__)


class RobustRequester:
    """
    Robust HTTP request handler with:
    - Automatic retries with exponential backoff
    - Rotating user agents
    - Cookie management
    - Session reuse
    - Error handling
    """
    
    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        use_session: bool = True,
        timeout: float = 30.0
    ):
        """
        Initialize robust requester.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
            use_session: Whether to reuse HTTP session
            timeout: Request timeout in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.use_session = use_session
        
        self.retry_config = RetryConfig(
            max_attempts=max_retries,
            base_delay=base_delay,
            max_delay=max_delay
        )
        
        # Initialize session if using httpx
        self.session = None
        if use_session and HTTPX_AVAILABLE:
            self.session = httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                headers=get_browser_headers()
            )
        elif use_session:
            self.session = requests.Session()
            self.session.headers.update(get_browser_headers())
    
    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        data: Optional[Any] = None,
        cookies: Optional[Dict] = None
    ) -> Tuple[Any, Optional[Dict]]:
        """
        Make HTTP request with current session or create new one.
        
        Returns:
            Tuple of (response, response_dict)
        """
        # Merge headers
        request_headers = get_browser_headers()
        if headers:
            request_headers.update(headers)
        
        # Rotate user agent occasionally
        if random.random() < 0.3:  # 30% chance to rotate
            request_headers['User-Agent'] = get_random_user_agent()
        
        try:
            if self.session:
                if method.upper() == 'GET':
                    response = self.session.get(
                        url,
                        headers=request_headers,
                        params=params,
                        cookies=cookies,
                        timeout=self.timeout
                    )
                elif method.upper() == 'POST':
                    response = self.session.post(
                        url,
                        headers=request_headers,
                        params=params,
                        json=json_data,
                        data=data,
                        cookies=cookies,
                        timeout=self.timeout
                    )
                elif method.upper() == 'HEAD':
                    response = self.session.head(
                        url,
                        headers=request_headers,
                        params=params,
                        cookies=cookies,
                        timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Unsupported method: {method}")
            else:
                # No session - use one-off request
                if HTTPX_AVAILABLE:
                    with httpx.Client(timeout=self.timeout) as client:
                        if method.upper() == 'GET':
                            response = client.get(url, headers=request_headers, params=params, cookies=cookies)
                        elif method.upper() == 'POST':
                            response = client.post(url, headers=request_headers, params=params, json=json_data, data=data, cookies=cookies)
                        elif method.upper() == 'HEAD':
                            response = client.head(url, headers=request_headers, params=params, cookies=cookies)
                        else:
                            raise ValueError(f"Unsupported method: {method}")
                else:
                    if method.upper() == 'GET':
                        response = requests.get(url, headers=request_headers, params=params, cookies=cookies, timeout=self.timeout)
                    elif method.upper() == 'POST':
                        response = requests.post(url, headers=request_headers, params=params, json=json_data, data=data, cookies=cookies, timeout=self.timeout)
                    elif method.upper() == 'HEAD':
                        response = requests.head(url, headers=request_headers, params=params, cookies=cookies, timeout=self.timeout)
                    else:
                        raise ValueError(f"Unsupported method: {method}")
            
            # Check status code
            response.raise_for_status()
            
            # Try to parse JSON if content-type suggests it
            response_dict = None
            content_type = response.headers.get('Content-Type', '').lower()
            if 'json' in content_type or 'application/json' in content_type:
                try:
                    if hasattr(response, 'json'):
                        response_dict = response.json()
                    else:
                        response_dict = json.loads(response.text)
                except:
                    pass
            
            return response, response_dict
            
        except Exception as e:
            # Add status code to exception if available
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                e.status_code = e.response.status_code
            raise
    
    def get(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        cookies: Optional[Dict] = None,
        retry: bool = True
    ) -> Tuple[Any, Optional[Dict]]:
        """
        Make GET request with retry logic.
        
        Returns:
            Tuple of (response, response_dict)
        """
        if retry:
            return retry_request(
                self._make_request,
                'GET',
                url,
                headers=headers,
                params=params,
                cookies=cookies,
                config=self.retry_config
            )
        else:
            return self._make_request('GET', url, headers=headers, params=params, cookies=cookies)
    
    def post(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        data: Optional[Any] = None,
        cookies: Optional[Dict] = None,
        retry: bool = True
    ) -> Tuple[Any, Optional[Dict]]:
        """Make POST request with retry logic"""
        if retry:
            return retry_request(
                self._make_request,
                'POST',
                url,
                headers=headers,
                params=params,
                json_data=json_data,
                data=data,
                cookies=cookies,
                config=self.retry_config
            )
        else:
            return self._make_request('POST', url, headers=headers, params=params, json_data=json_data, data=data, cookies=cookies)
    
    def head(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        cookies: Optional[Dict] = None
    ) -> Any:
        """Make HEAD request (for health checks)"""
        return self._make_request('HEAD', url, headers=headers, params=params, cookies=cookies)[0]
    
    def health_check(self, url: str, timeout: float = 5.0) -> bool:
        """
        Quick health check for endpoint.
        
        Args:
            url: URL to check
            timeout: Timeout for health check
        
        Returns:
            True if endpoint is healthy, False otherwise
        """
        try:
            old_timeout = self.timeout
            self.timeout = timeout
            response = self.head(url)
            self.timeout = old_timeout
            return response.status_code in [200, 301, 302, 304]
        except:
            return False
    
    def close(self):
        """Close session if using one"""
        if self.session:
            try:
                if hasattr(self.session, 'close'):
                    self.session.close()
            except:
                pass
            self.session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

