import os, sys
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)
from utils.browser_manager import BrowserManager

with BrowserManager(headless=True) as bm:
    page = bm.new_page()
    page.goto("https://www.foodbasics.ca/aisles/fruits-vegetables/vegetables/onions-leeks/yellow-onions/p/059749900133", wait_until="networkidle", timeout=60000)
    html = page.content()
    
    with open("fb_onion.html", "w") as f:
        f.write(html)
    print("Saved to fb_onion.html")
