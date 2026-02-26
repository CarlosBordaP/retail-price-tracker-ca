import sys
import json
import logging
import argparse
import os

# Ensure the root directory is in sys.path when running from different locations
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from scrapers.nofrills import NoFrillsScraper
from scrapers.foodbasics import FoodBasicsScraper
from scrapers.metro import MetroScraper
from utils.browser_manager import BrowserManager
from utils.unit_converter import UnitConverter

# Suppress debug logs for cleaner JSON output
logging.getLogger("WDM").setLevel(logging.ERROR)
logging.getLogger("scraper").setLevel(logging.ERROR)

def process_test_result(item, result):
    """Formats the result like main.py but returns a dict instead of saving to DB."""
    if result and result.get('price'):
        price = result['price']
        raw_weight = result.get('raw_weight', '')
        unit_price_text = result.get('unit_price_text', '')
        
        up_val, up_qty, up_unit = UnitConverter.parse_unit_price_string(unit_price_text)
        if up_val:
            unit_price, std_unit = UnitConverter.to_standard_unit(up_val, up_qty, up_unit)
            quantity, unit = up_qty, up_unit
        else:
            quantity, unit = UnitConverter.parse_quantity(raw_weight)
            unit_price, std_unit = UnitConverter.to_standard_unit(price, quantity, unit)
            
        pack_size = item.get('pack_size')
        if pack_size and isinstance(pack_size, (int, float)) and pack_size > 0:
            unit_price = unit_price / pack_size
            price = price / pack_size
        
        return {
            "status": "success",
            "data": {
                "product_id": item['id'],
                "product_name": item['name'],
                "store": item['store'],
                "extracted_price": price,
                "currency": result['currency'],
                "raw_weight": raw_weight,
                "unit": unit,
                "quantity": quantity,
                "unit_price": unit_price,
                "standard_unit": std_unit,
                "url": item['url']
            }
        }
    elif result and result.get('status') == 'blocked':
        return {"status": "error", "error": "Blocked by anti-bot protection."}
    else:
        return {"status": "error", "error": "Failed to extract required data (price or name)."}


def main():
    parser = argparse.ArgumentParser(description="Test a single URL and return JSON")
    parser.add_argument("--store", required=True, help="Store name (e.g., nofrills, foodbasics, metro)")
    parser.add_argument("--url", required=True, help="URL to scrape")
    parser.add_argument("--id", required=True, help="Product ID")
    parser.add_argument("--name", required=True, help="Product Name")
    parser.add_argument("--pack-size", type=float, default=None, help="Pack Size")
    args = parser.parse_args()

    scrapers = {
        "nofrills": NoFrillsScraper(),
        "foodbasics": FoodBasicsScraper(),
        "metro": MetroScraper()
    }

    scraper = scrapers.get(args.store)
    if not scraper:
        print(json.dumps({"status": "error", "error": f"Unknown store: {args.store}"}))
        sys.exit(1)

    item_mock = {
        "id": args.id,
        "name": args.name,
        "store": args.store,
        "url": args.url,
        "pack_size": args.pack_size
    }

    try:
        with BrowserManager(headless=True) as bm:
            result = scraper.run(args.url, browser_mgr=bm)
            final_result = process_test_result(item_mock, result)
            print(json.dumps(final_result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))

if __name__ == "__main__":
    main()
