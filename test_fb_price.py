import os, sys
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)
from bs4 import BeautifulSoup
from utils.browser_manager import BrowserManager

url = "https://www.foodbasics.ca/aisles/fruits-vegetables/vegetables/onions-leeks/yellow-onions/p/059749900133"

with BrowserManager(headless=True) as bm:
    html = bm.get_page_html(url, sleep_after=5)
    soup = BeautifulSoup(html, 'html.parser')
    
    price_tag = soup.select_one("span.price-update")
    print(f"Main Price span.price-update: {price_tag.get_text(strip=True) if price_tag else 'None'}")
    
    sec_price = soup.select_one(".pricing__secondary-price")
    print(f"Secondary Price .pricing__secondary-price: {sec_price.get_text(separator=' ', strip=True) if sec_price else 'None'}")
    
    main_price_block = soup.select_one("div.pi--prices")
    if main_price_block:
        print(f"Full price block text: {main_price_block.get_text(separator=' ', strip=True)}")
    else:
        print("No div.pi--prices found.")

