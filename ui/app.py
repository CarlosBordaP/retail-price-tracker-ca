from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
import os
import sys
import copy

app = FastAPI(title="Price Tracker Control UI")

# Config Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_FILE = os.path.join(BASE_DIR, "config", "products.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "config", "settings.json")
STATIC_DIR = os.path.join(BASE_DIR, "ui", "static")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Models for Request Bodies
class SettingsUpdate(BaseModel):
    enabled_stores: list[str]

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
