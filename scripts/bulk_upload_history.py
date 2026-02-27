"""
Bulk upload all historical data from local SQLite to Supabase.
Avoids duplicates by checking existing records in fact_market_price.

Usage:
    python scripts/bulk_upload_history.py
"""

import sqlite3
import sys
import os
import json
from datetime import datetime, date

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from storage.supabase_manager import SupabaseManager

LOCAL_DB = os.path.join(ROOT_DIR, "storage", "history.db")
PRODUCTS_JSON = os.path.join(ROOT_DIR, "config", "products.json")


def load_active_product_ids():
    """Load active product IDs from products.json."""
    with open(PRODUCTS_JSON, "r") as f:
        products = json.load(f)
    return set(p["id"] for p in products if p.get("active", True))


def get_existing_keys(sb):
    """Get existing (source_product_key, date_id) pairs from Supabase to avoid duplicates."""
    import psycopg2
    existing = set()
    with psycopg2.connect(sb._dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source_product_key, date_id 
                FROM capstone.fact_market_price 
                WHERE source_id IN (4, 5, 6)
            """)
            for key, dt in cur.fetchall():
                existing.add((key, dt))
    return existing


def main():
    sb = SupabaseManager()
    active_ids = load_active_product_ids()
    existing_keys = get_existing_keys(sb)
    
    print(f"📦 Active products: {len(active_ids)}")
    print(f"📦 Existing Supabase records: {len(existing_keys)}")

    # Read all local history, keeping only the latest per product per day
    conn_local = sqlite3.connect(LOCAL_DB)
    cur = conn_local.cursor()
    cur.execute("""
        SELECT product_id, store, product_name, price, unit_price, standard_unit, 
               unit, quantity, currency, url, timestamp
        FROM price_history
        ORDER BY product_id, timestamp DESC
    """)
    rows = cur.fetchall()
    conn_local.close()

    # Deduplicate: keep one record per (product_id, date)
    seen = {}
    for row in rows:
        pid, store, name, price, unit_price, std_unit, unit, qty, currency, url, ts = row
        
        # Only active products
        if pid not in active_ids:
            continue
        
        # Parse date
        try:
            dt = datetime.fromisoformat(ts).date()
        except:
            continue
        
        key = (pid, dt)
        if key not in seen:
            seen[key] = {
                "product_id": pid,
                "store": store,
                "product_name": name,
                "price": price,
                "unit_price": unit_price if unit_price else price,
                "standard_unit": std_unit if std_unit else "each",
                "unit": unit,
                "quantity": qty,
                "currency": currency,
                "url": url,
                "timestamp": ts,
            }

    print(f"📦 Unique (product, date) records from SQLite: {len(seen)}")

    # Upload, skipping duplicates
    uploaded = 0
    skipped = 0
    failed = 0

    for (pid, dt), data in sorted(seen.items()):
        # Check if already in Supabase
        if (pid, dt) in existing_keys:
            skipped += 1
            continue

        try:
            success = sb.insert_market_price(data)
            if success:
                uploaded += 1
                print(f"  ✅ {pid} @ {dt} -> ${data['unit_price']:.2f}")
            else:
                skipped += 1
                print(f"  ⏭️  {pid} @ {dt} (no alias/vendor)")
        except Exception as e:
            failed += 1
            print(f"  ❌ {pid} @ {dt}: {e}")

    print(f"\n🎉 Done!")
    print(f"   Uploaded: {uploaded}")
    print(f"   Skipped:  {skipped} (duplicates or unmapped)")
    print(f"   Failed:   {failed}")


if __name__ == "__main__":
    main()
