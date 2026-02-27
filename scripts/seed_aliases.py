"""
Seed script: generates product_mapping.csv and optionally inserts aliases into Supabase.

Usage:
    # Step 1: Generate mapping CSV for review
    python scripts/seed_aliases.py --generate

    # Step 2: After review, seed approved mappings
    python scripts/seed_aliases.py --seed
    
    # Also seed vendor records if needed
    python scripts/seed_aliases.py --seed-vendors
"""

import csv
import json
import os
import sys
import argparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

PRODUCTS_JSON = os.path.join(ROOT_DIR, "config", "products.json")
PRODUCTS_CSV = os.path.join(ROOT_DIR, "data", "products.csv")
MAPPING_CSV = os.path.join(ROOT_DIR, "data", "product_mapping.csv")


def load_dim_products():
    """Load the canonical dim_product list from data/products.csv."""
    products = {}
    with open(PRODUCTS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = int(row["product_id"])
            products[pid] = {
                "product_id": pid,
                "product_name": row["product_name"].strip(),
                "category": row["category"].strip(),
                "unit_id": int(row["unit_id"]),
            }
    return products


def load_scraper_products():
    """Load scraping products from config/products.json."""
    with open(PRODUCTS_JSON, "r") as f:
        return json.load(f)


def fuzzy_match(scraper_name: str, dim_products: dict):
    """
    Try to find the best match between a scraper product name and dim_product names.
    Returns (product_id, product_name, confidence) or None.
    """
    scraper_lower = scraper_name.lower()
    
    best_match = None
    best_score = 0

    for pid, dp in dim_products.items():
        dim_lower = dp["product_name"].lower()
        
        # Exact match
        if scraper_lower == dim_lower:
            return pid, dp["product_name"], "EXACT"

        # Check if dim name is contained in scraper name or vice versa
        if dim_lower in scraper_lower or scraper_lower in dim_lower:
            score = len(dim_lower) / max(len(scraper_lower), 1)
            if score > best_score:
                best_score = score
                best_match = (pid, dp["product_name"], "PARTIAL")

        # Check keyword overlap
        dim_words = set(dim_lower.split())
        scraper_words = set(scraper_lower.split())
        overlap = dim_words & scraper_words
        if len(overlap) >= 2:
            score = len(overlap) / max(len(dim_words), len(scraper_words))
            if score > best_score:
                best_score = score
                best_match = (pid, dp["product_name"], "KEYWORD")

    return best_match


# Hardcoded mapping overrides for known tricky cases
MANUAL_OVERRIDES = {
    # NoFrills
    "nf-chicken-breast": 12,   # Chicken Boneless Breast
    "nf-chicken-thigh": 9,     # Chicken Boneless Thigh
    "nf-pork-belly": 31,       # Pork Belly
    "nf-avocado": 26,          # Avocado
    "nf-mozzarella": 5,        # Mozzarella Cheese
    "nf-ground-beef": 21,      # Lean Ground Beef
    "nf-pork-shoulder": 7,     # Boneless Pork Shoulder
    "nf-cilantro": 8,          # Cilantro
    "nf-whipping-cream": 20,   # Whipping Cream 35
    "nf-sour-cream": 28,       # Sour Cream 14
    "nf-organic-romaine": 3,   # Romaine Hearts
    "nf-rice": 16,             # Rice Precooked
    "nf-limes": 2,             # Limes
    "nf-eggs": 11,             # Extra-Large Eggs
    "nf-vegetable-oil": 24,    # Vegetable Oil
    "nf-feta": 32,             # Feta Cheese
    "nf-pork-loin": 1,         # Pork Loin
    "nf-green-onion": 4,       # Green Onions
    "nf-corn": 19,             # Frozen Corn
    "nf-ground-pork": 15,      # Lean Ground Pork
    "nf-milk": 17,             # Milk 3.25
    "nf-plant-butter": 6,      # Unsalted Butter
    "nf-canola-oil": 24,       # Vegetable Oil (canola maps here too)
    "nf-eye-round-beef": 27,   # Beef Eye of Round
    "nf-onion": 10,            # Onions
    "nf-tortillas": 14,        # White Tortilla
    "nf-riceCooked": 16,       # Rice Precooked
    "nf-coffee": 25,           # Coffee

    # FoodBasics
    "fb-chicken-breast": 12,
    "fb-chicken-thigh": 9,
    "fb-pork-belly": 31,
    "fb-avocado": 26,
    "fb-mozzarella": 5,
    "fb-ground-beef": 21,
    "fb-pork-shoulder": 7,
    "fb-cilantro": 8,
    "fb-whipping-cream": 20,
    "fb-sour-cream": 28,
    "fb-romaine": 3,
    "fb-round-steak": 22,      # Beef Outside Round
    "fb-rice": 16,
    "fb-limes": 2,
    "fb-eggs": 11,
    "fb-vegetable-oil": 24,
    "fb-feta": 32,
    "fb-pork-loin": 1,
    "fb-green-onion": 4,
    "fb-corn": 19,
    "fb-ground-pork": 15,
    "fb-milk": 17,
    "fb-butter": 6,
    "fb-canola-oil": 24,
    "fb-eye-round-steak": 27,
    "fb-onions": 10,
    "fb-tortillas": 14,
    "fb-rice_precook": 16,
    "fb-coffee": 25,

    # Metro
    "me-chicken-breast": 12,
    "me-chicken-thigh": 9,
    "me-pork-belly": 31,
    "me-avocado": 26,
    "me-mozzarella": 5,
    "me-ground-beef": 21,
    "me-pork-shoulder": 7,
    "me-cilantro": 8,
    "me-whipping-cream": 20,
    "me-sour-cream": 28,
    "me-romaine": 3,
    "me-outside-round-roast": 22,
    "me-rice": 16,
    "me-limes": 2,
    "me-eggs": 11,
    "me-vegetable-oil": 24,
    "me-feta": 32,
    "me-pork-loin-roast": 1,
    "me-green-onion": 4,
    "me-corn": 19,
    "me-ground-pork": 15,
    "me-flank-steak": 37,      # Beef Flank Steak
    "me-milk": 17,
    "me-butter": 6,
    "me-canola-oil": 24,
    "me-eye-round-roast": 27,
    "me-onions": 10,
    "me-tortillas": 14,
    "me-riceprecook": 16,
    "me-coffee": 25,
}

SOURCE_MAP = {
    "nofrills": 4,
    "metro": 5,
    "foodbasics": 6,
}


def generate_mapping():
    """Generate product_mapping.csv for user review."""
    dim_products = load_dim_products()
    scraper_products = load_scraper_products()

    rows = []
    for sp in scraper_products:
        scraper_id = sp["id"]
        scraper_name = sp["name"]
        store = sp["store"]
        active = sp.get("active", True)
        source_id = SOURCE_MAP.get(store, 0)

        # Check manual override first
        if scraper_id in MANUAL_OVERRIDES:
            dim_pid = MANUAL_OVERRIDES[scraper_id]
            dp = dim_products.get(dim_pid)
            if dp:
                rows.append({
                    "scraper_id": scraper_id,
                    "scraper_name": scraper_name,
                    "store": store,
                    "source_id": source_id,
                    "active": active,
                    "dim_product_id": dim_pid,
                    "dim_product_name": dp["product_name"],
                    "dim_unit_id": dp["unit_id"],
                    "match_type": "MANUAL",
                    "approved": "Y",
                })
                continue

        # Try fuzzy match
        match = fuzzy_match(scraper_name, dim_products)
        if match:
            dim_pid, dim_name, match_type = match
            dp = dim_products.get(dim_pid)
            rows.append({
                "scraper_id": scraper_id,
                "scraper_name": scraper_name,
                "store": store,
                "source_id": source_id,
                "active": active,
                "dim_product_id": dim_pid,
                "dim_product_name": dim_name,
                "dim_unit_id": dp["unit_id"] if dp else 3,
                "match_type": match_type,
                "approved": "Y" if match_type == "EXACT" else "?",
            })
        else:
            rows.append({
                "scraper_id": scraper_id,
                "scraper_name": scraper_name,
                "store": store,
                "source_id": source_id,
                "active": active,
                "dim_product_id": "",
                "dim_product_name": "NO MATCH",
                "dim_unit_id": "",
                "match_type": "NONE",
                "approved": "N",
            })

    # Write CSV
    fieldnames = ["scraper_id", "scraper_name", "store", "source_id", "active",
                  "dim_product_id", "dim_product_name", "dim_unit_id", "match_type", "approved"]
    
    with open(MAPPING_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Generated mapping: {MAPPING_CSV}")
    print(f"   Total: {len(rows)} products")
    print(f"   Manual: {sum(1 for r in rows if r['match_type'] == 'MANUAL')}")
    print(f"   Fuzzy:  {sum(1 for r in rows if r['match_type'] in ('EXACT','PARTIAL','KEYWORD'))}")
    print(f"   None:   {sum(1 for r in rows if r['match_type'] == 'NONE')}")


def seed_aliases():
    """Read approved mappings from CSV and insert into Supabase."""
    from storage.supabase_manager import SupabaseManager
    sb = SupabaseManager()

    with open(MAPPING_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if row["approved"].strip().upper() != "Y":
                print(f"⏭️  Skipping {row['scraper_id']} (not approved)")
                continue
            
            source_id = int(row["source_id"])
            product_id = int(row["dim_product_id"])
            unit_id = int(row["dim_unit_id"])
            
            sb.upsert_alias(
                source_id=source_id,
                product_id=product_id,
                source_product_key=row["scraper_id"],
                source_product_name=row["scraper_name"],
                unit_id=unit_id,
            )
            count += 1
            print(f"✅ Seeded: {row['scraper_id']} -> product_id={product_id}")

    print(f"\n🎉 Done! Seeded {count} aliases.")


def seed_vendors():
    """Create retailer vendor records in Supabase."""
    from storage.supabase_manager import SupabaseManager
    sb = SupabaseManager()
    vendor_map = sb.ensure_vendors()
    print(f"✅ Vendors created/verified: {vendor_map}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product alias seeder")
    parser.add_argument("--generate", action="store_true", help="Generate mapping CSV")
    parser.add_argument("--seed", action="store_true", help="Seed approved aliases to Supabase")
    parser.add_argument("--seed-vendors", action="store_true", help="Seed vendor records")
    args = parser.parse_args()

    if args.generate:
        generate_mapping()
    elif args.seed:
        seed_aliases()
    elif args.seed_vendors:
        seed_vendors()
    else:
        parser.print_help()
