import os, sys
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)
from utils.browser_manager import BrowserManager

with BrowserManager(headless=True) as bm:
    html = bm.get_page_html("https://www.foodbasics.ca/aisles/fruits-vegetables/vegetables/onions-leeks/yellow-onions/p/059749900133")
    with open("fb_onion.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved to fb_onion.html")
