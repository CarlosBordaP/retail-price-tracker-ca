import logging
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logger = logging.getLogger("BrowserManager")

class BrowserManager:
    """Manages the lifecycle of a Playwright browser instance with stealth capabilities."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        # Using channel="chrome" can sometimes help be less detectable
        self.browser = self.playwright.chromium.launch(headless=self.headless, channel="chrome")
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="en-CA",
            timezone_id="America/Toronto"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def get_page_html(self, url: str, wait_for_selector: str = None, sleep_after: int = 15) -> str:
        """Navigates to a URL using stealth and returns the rendered HTML."""
        page = self.context.new_page()
        # Use the user's preferred Stealth apply method
        Stealth().apply_stealth_sync(page)
        
        try:
            logger.info(f"Navigating to {url} via Playwright (Headless={self.headless})...")
            # Navigate with a generous timeout
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Special handling for No Frills pickup modal
            try:
                # The "Yes" button is often used to confirm location
                yes_button = page.get_by_text("Yes", exact=True)
                if yes_button.is_visible(timeout=5000):
                    logger.info("Clicking No Frills pickup confirmation...")
                    yes_button.click()
                    time.sleep(2)
            except:
                pass

            # Simulate some human activity
            page.mouse.move(100, 100)
            time.sleep(1)
            page.mouse.wheel(0, 500) # Scroll down
            time.sleep(1)
            
            if wait_for_selector:
                page.wait_for_selector(wait_for_selector, timeout=20000)
            
            # Wait for content to stabilize
            if sleep_after:
                time.sleep(sleep_after)
                
            html = page.content()
            page.close()
            return html
        except Exception as e:
            logger.error(f"Playwright error fetching {url}: {e}")
            page.close()
            return ""
    def execute_script(self, url: str, script: str, sleep_after: int = 15) -> any:
        """Navigates to a URL and executes a JS script to extract data directly."""
        page = self.context.new_page()
        Stealth().apply_stealth_sync(page)
        
        try:
            logger.info(f"Navigating to {url} for script execution...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Modal handling
            try:
                yes_button = page.get_by_text("Yes", exact=False)
                if yes_button.is_visible(timeout=5000):
                    yes_button.click()
                    time.sleep(2)
            except:
                pass

            # Human mimicry
            page.mouse.wheel(0, 1000)
            time.sleep(2)
            page.mouse.wheel(0, -500)
            
            if sleep_after:
                logger.info(f"Waiting {sleep_after}s for dynamic content...")
                time.sleep(sleep_after)
                
            logger.info("Executing extraction script in browser...")
            data = page.evaluate(script)
            page.close()
            return data
        except Exception as e:
            logger.error(f"Script execution error: {e}")
            page.close()
            return None
