import json
import logging
import os
import argparse
import glob
from datetime import datetime
from scrapers.nofrills import NoFrillsScraper
from scrapers.foodbasics import FoodBasicsScraper
from scrapers.metro import MetroScraper
from storage.db_manager import DatabaseManager
from storage.csv_manager import CSVManager
from storage.supabase_manager import SupabaseManager
from alerts.notifier import Notifier
from utils.unit_converter import UnitConverter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/Users/carlosborda/Documents/Python/Learning/scraping/logs/tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Orchestrator")

def process_result(item, result, db, notifier, csv_mgr, sb=None):
    """Handles storage, notification, and CSV dataset for a scraper result."""
    p_id = item['id']
    name = item['name']
    store = item['store']
    url = item['url']

    if result and result.get('price'):
        # --- Unit Standardization ---
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
            
        # Optional parameter: pack_size (User request to convert 1 ea bag to per-unit cost)
        pack_size = item.get('pack_size')
        if pack_size and isinstance(pack_size, (int, float)) and pack_size > 0:
            unit_price = unit_price / pack_size
            price = price / pack_size # update base price string if needed, or leave base price and just adjust unit price
            # We focus on adjusting the unit_price for standardized comparison
        
        last_price = db.get_last_price(p_id)
        
        data_to_store = {
            "product_id": p_id,
            "store": store,
            "product_name": name,
            "price": price,
            "currency": result['currency'],
            "stock": result.get('stock', 'unknown'),
            "unit": unit,
            "quantity": quantity,
            "unit_price": unit_price,
            "standard_unit": std_unit,
            "url": url
        }
        db.save_price(data_to_store)
        csv_mgr.append_price(data_to_store)
        
        if last_price is not None and last_price != price:
            notifier.notify_change(name, last_price, price)
            
        logger.info(f"Success: {name} - ${price} (Unit Price: ${unit_price:.2f}/{std_unit})")
        
        # Upload to Supabase
        if sb:
            try:
                sb.insert_market_price(data_to_store)
            except Exception as e:
                logger.warning(f"Supabase upload failed for {name}: {e}")
        
        return True
    elif result and result.get('status') == 'blocked':
        logger.error(f"BLOCKED: {name} at {store} is protected by anti-bot. Please use folder import.")
    else:
        logger.warning(f"Failed to extract price for {name}")
    return False

def main():
    parser = argparse.ArgumentParser(description="Price Tracker CA Orchestrator")
    parser.add_argument("--local-file", help="Path to a local HTML file to parse")
    parser.add_argument("--product-id", help="Product ID for the local file")
    parser.add_argument("--import-all", action="store_true", help="Batch import all HTML files from html_imports folders")
    parser.add_argument("--url", help="Run a single product extraction by URL for debugging")
    parser.add_argument("--ui-mode", action="store_true", help="Run in UI mode, updating scraper_state.json")
    args = parser.parse_args()

    db = DatabaseManager()
    csv_mgr = CSVManager()
    notifier = Notifier(webhook_url=os.getenv("DISCORD_WEBHOOK"))
    
    # Initialize Supabase manager
    try:
        sb = SupabaseManager()
        logger.info("Supabase connection initialized.")
    except Exception as e:
        logger.warning(f"Supabase init failed, running in local-only mode: {e}")
        sb = None
    
    scrapers = {
        "nofrills": NoFrillsScraper(),
        "foodbasics": FoodBasicsScraper(),
        "metro": MetroScraper()
    }

    config_path = "/Users/carlosborda/Documents/Python/Learning/scraping/config/products.json"
    settings_path = "/Users/carlosborda/Documents/Python/Learning/scraping/config/settings.json"
    
    # Load Products
    try:
        with open(config_path, "r") as f:
            all_products = json.load(f)
            # US01: Ignorar productos inactivos/pausados
            products = [p for p in all_products if p.get("active", True)]
            if len(products) < len(all_products):
                logger.info(f"Loaded {len(products)} active products (ignored {len(all_products)-len(products)} paused).")
    except FileNotFoundError:
        logger.error("Products config file not found.")
        return

    # Load Settings (Filter stores)
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
                enabled_stores = settings.get("enabled_stores", [])
                original_count = len(products)
                products = [p for p in products if p['store'] in enabled_stores]
                if len(products) < original_count:
                    logger.info(f"Filtered products: {len(products)} active (from {original_count} total) based on enabled_stores.")
        except Exception as e:
            logger.warning(f"Could not load settings.json, running all stores. Error: {e}")

    # Batch Import Mode
    if args.import_all:
        logger.info("Starting Batch Import from 'html_imports/'...")
        import_base = "/Users/carlosborda/Documents/Python/Learning/scraping/html_imports"
        
        for store in ["walmart", "costco"]:
            store_dir = os.path.join(import_base, store)
            html_files = glob.glob(os.path.join(store_dir, "*.html"))
            
            for file_path in html_files:
                # Expecting filename to be ID.html (e.g. wm-ca-001.html)
                p_id = os.path.basename(file_path).replace(".html", "")
                product = next((p for p in products if p['id'] == p_id), None)
                
                if product:
                    logger.info(f"Importing {file_path} for {product['name']}...")
                    scraper = scrapers.get(store)
                    result = scraper.run_local(file_path)
                    process_result(product, result, db, notifier)
                else:
                    logger.warning(f"File {p_id}.html ignored: Product ID not found in config.")
        return

    # Single File Semi-Automatic Mode
    if args.local_file:
        # (Legacy single-file logic kept for flexibility)
        if not args.product_id:
            logger.error("Error: --product-id is required when using --local-file")
            return
        product = next((p for p in products if p['id'] == args.product_id), None)
        if product:
            result = scrapers.get(product['store']).run_local(args.local_file)
            process_result(product, result, db, notifier, csv_mgr, sb)
        return

    # Single URL Debug Mode
    if args.url:
        logger.info(f"Running single product debug for URL: {args.url}")
        product = next((p for p in products if p['url'] == args.url), None)
        if not product:
            logger.error("URL not found in products.json. Please ensure it matches exactly.")
            return
            
        from utils.browser_manager import BrowserManager
        with BrowserManager(headless=True) as bm:
            scraper = scrapers.get(product['store'])
            result = scraper.run(product['url'], browser_mgr=bm)
            process_result(product, result, db, notifier, csv_mgr, sb)
        return

    # Automated Mode
    logger.info("Starting Automated Scan (Browser Mode with Playwright)...")
    from utils.browser_manager import BrowserManager
    import random
    random.shuffle(products) 
    
    with BrowserManager(headless=True) as bm:
        # 1. No Frills Flyer Scan (Bulk) - Disabled for specific product testing
        # logger.info("Extracting No Frills Flyer...")
        # nf_scraper = NoFrillsScraper()
        # flyer_url = "https://www.nofrills.ca/en/deals/flyer"
        # flyer_results = nf_scraper.run_flyer(flyer_url, browser_mgr=bm)
        
        # for res in flyer_results:
        #     mock_item = {
        #         "id": res["id"],
        #         "name": res["name"],
        #         "store": "nofrills",
        #         "url": res["url"]
        #     }
        #     process_result(mock_item, res, db, notifier, csv_mgr)
        
        # logger.info(f"Imported {len(flyer_results)} items from No Frills Flyer.")

        # 2. Individual Product Scan (No Frills PDP, Costco, etc.)
        state_file = "/Users/carlosborda/Documents/Python/Learning/scraping/data/scraper_state.json"
        completed_ids = []
        total_products = len(products)
        
        for idx, item in enumerate(products):
            if args.ui_mode:
                try:
                    with open(state_file, "w") as f:
                        json.dump({
                            "status": "running",
                            "progress": idx,
                            "total": total_products,
                            "current_product": item['name'],
                            "completed_ids": completed_ids
                        }, f)
                except Exception as e:
                    logger.error(f"Failed to write state: {e}")
                    
            scraper = scrapers.get(item['store'])
            if scraper:
                try:
                    result = scraper.run(item['url'], browser_mgr=bm)
                    
                    # Retry once if blocked
                    if result and result.get('status') == 'blocked':
                        logger.warning(f"Blocked on {item['name']}. Retrying in 45s...")
                        import time
                        time.sleep(45)
                        result = scraper.run(item['url'], browser_mgr=bm)
                    
                    process_result(item, result, db, notifier, csv_mgr, sb)
                    completed_ids.append(item['id'])
                except Exception as e:
                    logger.error(f"Error processing {item['name']}: {e}")
                    
        # Final state update
        if args.ui_mode:
            try:
                with open(state_file, "w") as f:
                    json.dump({
                        "status": "completed",
                        "progress": total_products,
                        "total": total_products,
                        "current_product": "Done",
                        "completed_ids": completed_ids
                    }, f)
            except Exception:
                pass

if __name__ == "__main__":
    main()
