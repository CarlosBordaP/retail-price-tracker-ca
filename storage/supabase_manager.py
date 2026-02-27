"""
Supabase PostgreSQL Manager for Price Tracker.
Handles connections, alias lookups, and fact insertions 
into the capstone schema on Supabase.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import date, datetime
import os
import logging

logger = logging.getLogger("supabase_manager")

class SupabaseManager:
    """Manages connections and operations against the capstone Supabase schema."""

    # Store key -> source_id mapping
    SOURCE_MAP = {
        "nofrills": 4,
        "metro": 5,
        "foodbasics": 6,
    }

    # Store key -> vendor_id mapping (will be set after vendor creation)
    VENDOR_MAP = {}

    # Scraper standard_unit -> dim_unit.unit_id
    UNIT_MAP = {
        "kg": 1,
        "l": 2,
        "each": 3,
        "unit": 3,
    }

    GEO_ID_BURLINGTON = 4  # Burlington, ON

    def __init__(self):
        load_dotenv()
        self._dsn = (
            f"host={os.getenv('DB_HOST')} "
            f"dbname={os.getenv('DB_NAME')} "
            f"user={os.getenv('DB_USER')} "
            f"password={os.getenv('DB_PASSWORD')} "
            f"port={os.getenv('DB_PORT')} "
            f"sslmode=require"
        )
        self._load_vendor_map()

    # ── Connection ────────────────────────────────────────────
    def _conn(self):
        return psycopg2.connect(self._dsn)

    def _load_vendor_map(self):
        """Load vendor_id mappings for our retailers."""
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT vendor_id, vendor_name 
                        FROM capstone.dim_vendor 
                        WHERE vendor_name IN ('No Frills', 'Metro', 'Food Basics')
                    """)
                    for vid, vname in cur.fetchall():
                        key = vname.lower().replace(" ", "")
                        if key == "nofrills":
                            self.VENDOR_MAP["nofrills"] = vid
                        elif key == "metro":
                            self.VENDOR_MAP["metro"] = vid
                        elif key == "foodbasics":
                            self.VENDOR_MAP["foodbasics"] = vid
        except Exception as e:
            logger.warning(f"Could not load vendor map: {e}")

    # ── Alias Resolution ──────────────────────────────────────
    def resolve_alias(self, source_product_key: str, source_id: int):
        """Looks up a product alias and returns (product_id, unit_id) or None."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT product_id, unit_id 
                    FROM capstone.product_alias 
                    WHERE source_product_key = %s AND source_id = %s
                """, (source_product_key, source_id))
                row = cur.fetchone()
                return row if row else None

    # ── Date Management ───────────────────────────────────────
    def ensure_date(self, dt: date):
        """Inserts a date into dim_date if it doesn't already exist."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM capstone.dim_date WHERE date_id = %s", (dt,))
                if cur.fetchone():
                    return
                
                month_name = dt.strftime("%B")
                day_name = dt.strftime("%A")
                year = dt.year
                week = dt.isocalendar()[1]
                
                # Determine season (Northern Hemisphere)
                month = dt.month
                if month in (12, 1, 2):
                    season = "Winter"
                elif month in (3, 4, 5):
                    season = "Spring"
                elif month in (6, 7, 8):
                    season = "Summer"
                else:
                    season = "Fall"

                cur.execute("""
                    INSERT INTO capstone.dim_date (date_id, month_name, day_name, season, year, week_number)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (dt, month_name, day_name, season, year, week))
                conn.commit()

    # ── Fact Insertion ────────────────────────────────────────
    def insert_market_price(self, data: dict):
        """
        Inserts a record into fact_market_price.
        
        data should contain:
            - product_id (from scraper, e.g. 'nf-chicken-breast')
            - store (e.g. 'nofrills')
            - unit_price (normalized price)
            - standard_unit (e.g. 'kg')
            - timestamp (ISO string or datetime)
        """
        store = data.get("store")
        source_id = self.SOURCE_MAP.get(store)
        vendor_id = self.VENDOR_MAP.get(store)
        scraper_product_key = data.get("product_id")

        if not source_id or not vendor_id:
            logger.warning(f"No source/vendor mapping for store '{store}'. Skipping upload.")
            return False

        # Resolve the alias
        alias = self.resolve_alias(scraper_product_key, source_id)
        if not alias:
            logger.warning(f"No alias found for product '{scraper_product_key}' (source_id={source_id}). Skipping.")
            return False

        dim_product_id, alias_unit_id = alias

        # Determine date
        ts = data.get("timestamp")
        if isinstance(ts, str):
            scrape_date = datetime.fromisoformat(ts).date()
        elif isinstance(ts, datetime):
            scrape_date = ts.date()
        else:
            scrape_date = date.today()

        # Ensure dim_date exists
        self.ensure_date(scrape_date)

        # Determine unit_id
        std_unit = data.get("standard_unit", "each")
        unit_id = alias_unit_id or self.UNIT_MAP.get(std_unit, 3)

        # Price
        price_base = data.get("unit_price", data.get("price", 0.0))

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO capstone.fact_market_price 
                        (date_id, geo_id, vendor_id, source_id, product_id, unit_id, price_base, source_product_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    scrape_date,
                    self.GEO_ID_BURLINGTON,
                    vendor_id,
                    source_id,
                    dim_product_id,
                    unit_id,
                    round(price_base, 2),
                    scraper_product_key
                ))
                conn.commit()
                logger.info(f"Uploaded {scraper_product_key} -> product_id={dim_product_id} @ ${price_base:.2f} for {scrape_date}")
                return True

    # ── Alias Seeding ─────────────────────────────────────────
    def upsert_alias(self, source_id: int, product_id: int, source_product_key: str, 
                     source_product_name: str, unit_id: int):
        """Inserts or updates a product alias."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                # Check if exists
                cur.execute("""
                    SELECT alias_id FROM capstone.product_alias 
                    WHERE source_product_key = %s AND source_id = %s
                """, (source_product_key, source_id))
                
                if cur.fetchone():
                    cur.execute("""
                        UPDATE capstone.product_alias 
                        SET product_id = %s, source_product_name = %s, unit_id = %s, updated_at = now()
                        WHERE source_product_key = %s AND source_id = %s
                    """, (product_id, source_product_name, unit_id, source_product_key, source_id))
                else:
                    cur.execute("""
                        INSERT INTO capstone.product_alias 
                            (source_id, product_id, source_product_key, source_product_name, unit_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (source_id, product_id, source_product_key, source_product_name, unit_id))
                
                conn.commit()

    # ── Vendor Seeding ────────────────────────────────────────
    def ensure_vendors(self):
        """Creates retailer vendors if they don't exist."""
        retailers = [
            ("No Frills", "RETAILER"),
            ("Metro", "RETAILER"),
            ("Food Basics", "RETAILER"),
        ]
        with self._conn() as conn:
            with conn.cursor() as cur:
                for name, vtype in retailers:
                    cur.execute("""
                        INSERT INTO capstone.dim_vendor (vendor_name, vendor_type)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (name, vtype))
                conn.commit()
        # Reload the vendor map
        self._load_vendor_map()
        return self.VENDOR_MAP
