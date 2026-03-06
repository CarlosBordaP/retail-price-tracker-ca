import os, sys
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)
from storage.supabase_manager import SupabaseManager

sb = SupabaseManager()
# source_id: int, product_id: int, source_product_key: str, source_product_name: str, unit_id: int
# Mapping 'Rice Precooked' (ID 16)
# Standard unit for Rice might be 3 (each) or something else. I will pass 3 for now, or fetch from existing.

items = [
    (1, 16, "nf-riceCooked", "Rice Precooked", 3),
    (2, 16, "me-rice", "Jasmin Rice", 3),
    (2, 16, "me-riceprecook", "Rice Precooked", 3),
    (3, 16, "fb-rice_precook", "Rice Precooked", 3),
]

for source_id, dim_id, key, name, unit_id in items:
    sb.upsert_alias(source_id, dim_id, key, name, unit_id)
    print(f"Upserted alias {key} -> {dim_id} (Source {source_id})")

