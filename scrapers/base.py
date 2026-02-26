import requests
import time
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseScraper(ABC):
    def __init__(self, user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive"
        })
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_html(self, url: str, browser_mgr=None) -> Optional[str]:
        """Fetches HTML using either requests (legacy) or Playwright (browser)."""
        if browser_mgr:
            # Browser-based fetching (Playwright)
            try:
                # Add a natural random jitter before opening browser
                import random
                delay = random.uniform(2, 5)
                time.sleep(delay)
                
                # We use a generic selector or just wait for body for flexibility
                html = browser_mgr.get_page_html(url)
                return html
            except Exception as e:
                self.logger.error(f"Browser fetch error: {e}")
                return None
        else:
            # Legacy Request-based fetching
            try:
                import random
                delay = random.uniform(5, 15)
                self.logger.info(f"Compliance delay (Legacy): {delay:.2f}s")
                time.sleep(delay)
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except Exception as e:
                self.logger.error(f"Request fetch error for {url}: {e}")
                return None

    def _clean_price(self, price_str: str) -> Optional[float]:
        """Cleans price strings like '$2.49' or '56¢' and returns a float."""
        if not price_str:
            return None
        
        # Remove whitespace and common symbols
        clean = price_str.strip()
        
        # Handle cents (¢ or c)
        is_cents = False
        if '¢' in clean or (clean.endswith('c') and not clean.endswith('cc')): # Basic check for 'c' suffix
            is_cents = True
            clean = re.sub(r'[¢c]', '', clean, flags=re.IGNORECASE)
            
        # Handle multi-line strings (No Frills flyer often has newlines)
        clean = clean.replace('\n', ' ').replace('\r', ' ')
        
        # Prioritize the first currency value found (e.g. from "sale: $4.00, was: $5.00")
        # We look for something like $4.00 or 56¢
        price_match = re.search(r'(\d+\.\d+|\d+)[\s]*[¢c]|\$[\s]*(\d+\.\d+|\d+)', clean)
        if price_match:
            # If it's a $X match
            if price_match.group(2):
                return float(price_match.group(2))
            # If it's a X¢ match
            if price_match.group(1):
                return float(price_match.group(1)) / 100.0

        # Fallback to the broad cleaning if the specific regex didn't hit
        # Remove common text prefixes
        clean = re.sub(r'^[a-zA-Z\s:]+', '', clean)
        
        # Remove currency symbols and commas
        clean = re.sub(r'[$,]', '', clean)
        
        try:
            val = float(clean)
            return val / 100.0 if is_cents else val
        except ValueError:
            # Try finding any float inside
            match = re.search(r'(\d+\.\d+)', clean)
            if match:
                return float(match.group(1))
            self.logger.error(f"Could not convert price string to float: {price_str}")
            return None

    @abstractmethod
    def parse(self, html: str) -> Dict[str, any]:
        """Specific parsing logic for each store."""
        pass

    def run(self, url: str, browser_mgr=None) -> Optional[Dict[str, any]]:
        """Executes the scraper for a given URL."""
        html = self._get_html(url, browser_mgr=browser_mgr)
        if html:
            if "Verify Your Identity" in html or "Bot Protection" in html:
                self.logger.warning(f"Access blocked by anti-bot for {url}")
                return {"status": "blocked", "price": None}
            
            result = self.parse(html)
            if isinstance(result, list):
                return result[0] if result else None
            return result
        return None

    def run_local(self, file_path: str) -> Optional[Dict[str, any]]:
        """Parses a local HTML file (Semi-Automatic mode)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html = f.read()
            return self.parse(html)
        except Exception as e:
            self.logger.error(f"Error reading local file {file_path}: {e}")
            return None
