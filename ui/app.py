from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
import os
import sys
import copy
import subprocess
import plistlib
from datetime import datetime

app = FastAPI(title="Price Tracker Control UI")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLIST_FILE = os.path.join(BASE_DIR, "com.carlos.pricescraper.plist")
PRODUCTS_FILE = os.path.join(BASE_DIR, "config", "products.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "config", "settings.json")
STATE_FILE = os.path.join(BASE_DIR, "data", "scraper_state.json")
STATIC_DIR = os.path.join(BASE_DIR, "ui", "static")

# Add storage path to sys.path so we can import db_manager
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from storage.db_manager import DatabaseManager
from storage.csv_manager import CSVManager
from storage.supabase_manager import SupabaseManager
import logging

logger = logging.getLogger("ui_app")

db = DatabaseManager()
csv_manager = CSVManager()

# Initialize Supabase manager
try:
    sb = SupabaseManager()
except Exception as e:
    logger.warning(f"Supabase init failed in UI: {e}")
    sb = None

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Models for Request Bodies
class SettingsUpdate(BaseModel):
    enabled_stores: list[str]

class ScheduleUpdate(BaseModel):
    hour: int
    minute: int

class SyncResolveRequest(BaseModel):
    product_id: str
    date: str
    direction: str # "push" or "pull"

class Product(BaseModel):
    id: str
    name: str
    store: str
    url: str
    active: bool = True
    pack_size: float | None = None

class ProductUpdate(BaseModel):
    name: str | None = None
    store: str | None = None
    url: str | None = None
    active: bool | None = None
    pack_size: float | None = None

class PersistRequest(BaseModel):
    product_id: str
    store: str
    product_name: str
    price: float
    currency: str = "$"
    stock: bool = True
    unit: str = "each"
    quantity: float = 1.0
    unit_price: float | None = None
    standard_unit: str | None = None
    url: str | None = None
    pack_size: float | None = None

class ToggleStatus(BaseModel):
    active: bool

# Helpers
def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        return []
    with open(PRODUCTS_FILE, "r") as f:
        return json.load(f)

def save_products(products):
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(products, f, indent=4)

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/api/products")
async def get_products():
    return load_products()

@app.post("/api/products")
async def add_product(product: Product):
    products = load_products()
    if any(p.get("id") == product.id for p in products):
        raise HTTPException(status_code=400, detail="Product ID already exists")
    
    new_product = product.model_dump(exclude_none=True)
    products.append(new_product)
    save_products(products)
    return new_product

@app.put("/api/products/{product_id}")
async def update_product(product_id: str, product_update: ProductUpdate):
    products = load_products()
    for i, p in enumerate(products):
        if p.get("id") == product_id:
            updates = product_update.model_dump(exclude_unset=True, exclude_none=True)
            products[i].update(updates)
            
            # Handle pack_size removal if explicitly set to null/empty in a real form (here we just use exclude_unset)
            if "pack_size" in product_update.model_fields_set and product_update.pack_size is None:
               if "pack_size" in products[i]:
                   del products[i]["pack_size"]

            save_products(products)
            return products[i]
    raise HTTPException(status_code=404, detail="Product not found")

@app.patch("/api/products/{product_id}/toggle")
async def toggle_product(product_id: str, status: ToggleStatus):
    products = load_products()
    for i, p in enumerate(products):
        if p.get("id") == product_id:
            products[i]["active"] = status.active
            save_products(products)
            return {"id": product_id, "active": status.active}
    raise HTTPException(status_code=404, detail="Product not found")

@app.delete("/api/products/{product_id}")
async def delete_product(product_id: str):
    products = load_products()
    initial_len = len(products)
    products = [p for p in products if p.get("id") != product_id]
    if len(products) == initial_len:
        raise HTTPException(status_code=404, detail="Product not found")
    
    save_products(products)
    return {"message": "Product deleted successfully"}

@app.get("/api/settings")
async def get_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"enabled_stores": ["nofrills", "foodbasics", "metro"]}
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

@app.put("/api/settings")
async def update_settings(settings: SettingsUpdate):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.model_dump(), f, indent=4)
    return settings.model_dump()

@app.get("/api/schedule")
async def get_schedule():
    if not os.path.exists(PLIST_FILE):
        raise HTTPException(status_code=404, detail="Plist file not found")
    try:
        with open(PLIST_FILE, "rb") as f:
            plist_data = plistlib.load(f)
            interval = plist_data.get("StartCalendarInterval", {})
            return {"hour": interval.get("Hour", 12), "minute": interval.get("Minute", 50)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read plist: {e}")

@app.put("/api/schedule")
async def update_schedule(schedule: ScheduleUpdate):
    if not os.path.exists(PLIST_FILE):
        raise HTTPException(status_code=404, detail="Plist file not found")
    try:
        # Load
        with open(PLIST_FILE, "rb") as f:
            plist_data = plistlib.load(f)
            
        # Update
        if "StartCalendarInterval" not in plist_data:
            plist_data["StartCalendarInterval"] = {}
        plist_data["StartCalendarInterval"]["Hour"] = schedule.hour
        plist_data["StartCalendarInterval"]["Minute"] = schedule.minute
        
        # Save
        with open(PLIST_FILE, "wb") as f:
            plistlib.dump(plist_data, f)
            
        # Reload launchd
        # Assuming we run this as the user, we unload and load
        try:
            subprocess.run(["launchctl", "unload", PLIST_FILE], check=False, capture_output=True)
            subprocess.run(["launchctl", "load", PLIST_FILE], check=True, capture_output=True)
        except Exception as e:
            logger.warning(f"Could not automatically reload launchctl: {e}")
            return {"status": "success", "message": "Schedule updated in plist, but launchctl reload failed or requires manual restart."}
            
        return {"status": "success", "message": "Schedule updated and applied"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {e}")

@app.post("/api/products/{product_id}/test")
async def test_product(product_id: str):
    import subprocess
    products = load_products()
    product = next((p for p in products if p.get("id") == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    tester_script = os.path.join(BASE_DIR, "utils", "tester.py")
    
    cmd = [
        sys.executable, tester_script,
        "--store", product.get("store"),
        "--url", product.get("url"),
        "--id", product.get("id"),
        "--name", product.get("name")
    ]
    
    if product.get("pack_size"):
        cmd.extend(["--pack-size", str(product.get("pack_size"))])
        
    try:
        # Run subprocess and capture output
        process = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Parse JSON output from the tester script
        result = json.loads(process.stdout.strip().split("\n")[-1])
        return result
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Scraper error: {e.stderr}")
    except json.JSONDecodeError as e:
         raise HTTPException(status_code=500, detail=f"Failed to parse scraper output. Output was: {process.stdout}")

@app.get("/api/history")
async def get_history(days: int = 7, active_only: bool = True):
    try:
        # If days is 0, fetch all time
        fetch_days = None if days == 0 else days
        data = db.get_history(days=fetch_days)
        
        # Always filter inactive products as requested
        active_ids = set()
        try:
            with open(PRODUCTS_FILE, "r") as f:
                products = json.load(f)
                for p in products:
                    if p.get("active", True):
                        active_ids.add(p.get("id"))
        except Exception:
            pass
            
        if active_ids:
            data = [d for d in data if d["id"] in active_ids]
            
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scrape/start")
async def start_scraper():
    import subprocess
    # Check if a scrape is already running by checking the state file
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                if state.get("status") == "running":
                    raise HTTPException(status_code=400, detail="Scraper is already running")
        except json.JSONDecodeError:
            pass # File corrupted, let's start a new one
            
    # Initialize state file
    with open(STATE_FILE, "w") as f:
        json.dump({
            "status": "running",
            "progress": 0,
            "total": 0,
            "current_product": "Initializing...",
            "completed_ids": []
        }, f)
        
    main_script = os.path.join(BASE_DIR, "main.py")
    
    # Launch main.py with --ui-mode in the background
    # We don't block the API, we just spin it up
    try:
        subprocess.Popen(
            [sys.executable, main_script, "--ui-mode"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"message": "Scraper started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scraper: {str(e)}")

@app.post("/api/scrape/stop")
async def stop_scraper():
    if not os.path.exists(STATE_FILE):
        return {"status": "idle"}
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            
        if state.get("status") == "running":
            state["status"] = "cancelling"
            state["current_product"] = "Stopping..."
            with open(STATE_FILE, "w") as f:
                json.dump(state, f)
            return {"message": "Cancellation requested"}
        else:
            return {"message": f"Scraper is not running (status: {state.get('status')})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping scraper: {e}")

@app.get("/api/scrape/status")
async def get_scrape_status():
    if not os.path.exists(STATE_FILE):
        return {"status": "idle"}
        
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"status": "error", "message": "Could not read status file"}

@app.post("/api/history/persist")
async def persist_history(data: PersistRequest):
    try:
        payload = data.dict()
        # Ensure unit_price and standard_unit are set if missing
        if payload.get("unit_price") is None:
            payload["unit_price"] = payload["price"]
        if payload.get("standard_unit") is None:
            payload["standard_unit"] = payload["unit"]
            
        # Ensure timestamp is set to local time
        if not payload.get("timestamp"):
            payload["timestamp"] = datetime.now().isoformat()
            
        db.save_price(payload)
        csv_manager.append_price(payload)
        
        # Also upload to Supabase
        if sb:
            try:
                sb.insert_market_price(payload)
            except Exception as e:
                logger.warning(f"Supabase upload failed during persist: {e}")
        
        return {"status": "success", "message": "Price persisted to history"}
    except Exception as e:
        logger.error(f"Persistence failed for {data.product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sync/discrepancies")
async def get_discrepancies(days: int = 7):
    # Get local history
    local_data = db.get_history(days=days)
    
    # Get remote history
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    remote_data = sb.get_recent_prices(days=days)
    
    # Map local_data into a flat format
    local_flat = {}
    stores = {}
    names = {}
    for item in local_data:
        p_id = item["id"]
        stores[p_id] = item["store"]
        names[p_id] = item["name"]
        for date_str, price in item.get("history", {}).items():
            local_flat[(p_id, date_str)] = price
            
    remote_flat = {}
    for item in remote_data:
        p_id = item["product_id"]
        remote_flat[(p_id, item["date"])] = item["price"]

    # Compare
    all_keys = set(local_flat.keys()).union(set(remote_flat.keys()))
    discrepancies = []
    
    products = load_products()
    product_map = {p["id"]: p for p in products}

    for p_id, date_str in all_keys:
        product_info = product_map.get(p_id, {})
        # Skip paused products
        if product_info.get("active", True) is False:
            continue
            
        local_price = local_flat.get((p_id, date_str))
        remote_price = remote_flat.get((p_id, date_str))
        
        # Only add if one is missing or absolute difference > 0.01
        if local_price is None or remote_price is None or abs(local_price - float(remote_price)) > 0.01:
            discrepancies.append({
                "product_id": p_id,
                "product_name": names.get(p_id) or product_info.get("name", "Unknown"),
                "store": stores.get(p_id) or product_info.get("store", "Unknown"),
                "date": date_str,
                "local_price": local_price,
                "remote_price": float(remote_price) if remote_price else None
            })
            
    return sorted(discrepancies, key=lambda x: (x["date"], x["product_id"]), reverse=True)

@app.post("/api/sync/resolve")
async def resolve_sync(req: SyncResolveRequest):
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    if req.direction == "push":
        # Push to Supabase from local
        data = db.get_price_record(req.product_id, req.date)
        if not data:
            raise HTTPException(status_code=404, detail="Local record not found")
        
        # Ensure timestamp is string
        if isinstance(data.get("timestamp"), str) == False:
            data["timestamp"] = str(data["timestamp"])
            
        try:
            success = sb.insert_market_price(data)
            if not success:
                raise HTTPException(status_code=400, detail="Supabase rejected the data. The product likely lacks an alias mapping in Supabase (dim_product/product_alias).")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
            
        return {"status": "success", "message": "Pushed to remote"}
            
    elif req.direction == "pull":
        products = load_products()
        p = next((x for x in products if x["id"] == req.product_id), None)
        if not p:
            raise HTTPException(status_code=404, detail="Product not found in config")
            
        # Get remote price directly from the discrepancies logic
        remote_data = sb.get_recent_prices(days=30)
        remote_item = next((x for x in remote_data if x["product_id"] == req.product_id and x["date"] == req.date), None)
        if not remote_item:
            raise HTTPException(status_code=404, detail="Remote record not found")
            
        data = {
            "product_id": req.product_id,
            "store": p["store"],
            "product_name": p["name"],
            "price": float(remote_item["price"]),
            "currency": "$",
            "stock": "unknown",
            "unit": "each",
            "quantity": 1.0,
            "unit_price": float(remote_item["price"]),
            "standard_unit": "each",
            "url": p["url"],
            "timestamp": f"{req.date}T12:00:00"
        }
        db.save_price(data)
        return {"status": "success", "message": "Pulled to local"}
    else:
        raise HTTPException(status_code=400, detail="Invalid direction")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
