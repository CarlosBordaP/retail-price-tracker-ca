import os
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
from storage.supabase_manager import SupabaseManager

sb = SupabaseManager()
with sb._conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT product_id, product_name FROM capstone.dim_product WHERE product_name ILIKE '%rice%'")
        products = cur.fetchall()
        print("Rice products in dim_product:")
        for p in products:
            print(f"ID: {p[0]}, Name: {p[1]}")
