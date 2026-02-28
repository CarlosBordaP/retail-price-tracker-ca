import sqlite3
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_path="/Users/carlosborda/Documents/Python/Learning/scraping/storage/history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Creates tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    store TEXT NOT NULL,
                    product_name TEXT,
                    price REAL,
                    currency TEXT,
                    stock TEXT,
                    unit TEXT,
                    quantity REAL,
                    unit_price REAL,
                    standard_unit TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    url TEXT
                )
            """)
            conn.commit()

    def save_price(self, data: dict):
        """Inserts a new price record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO price_history (
                    product_id, store, product_name, price, currency, stock, 
                    unit, quantity, unit_price, standard_unit, url, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("product_id"),
                data.get("store"),
                data.get("product_name"),
                data.get("price"),
                data.get("currency"),
                data.get("stock"),
                data.get("unit"),
                data.get("quantity"),
                data.get("unit_price"),
                data.get("standard_unit"),
                data.get("url"),
                data.get("timestamp", datetime.now().isoformat())
            ))
            conn.commit()

    def get_last_price(self, product_id: str):
        """Retrieves the most recent price for a product to detect changes."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT price FROM price_history 
                WHERE product_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (product_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_history(self, days=7):
        """Retrieves price history grouped by product. If days=None, returns all history."""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT 
                    product_id,
                    product_name,
                    store,
                    COALESCE(unit_price, price) as price,
                    standard_unit,
                    DATE(timestamp) as date
                FROM price_history
            """
            
            if days:
                query += f" WHERE timestamp >= date('now', '-{days} days') "
                
            query += " ORDER BY product_id, timestamp DESC"
                
            cursor = conn.execute(query)
            
            rows = cursor.fetchall()
            
            # Format: { "nf-chicken": { "id": "...", "name": "...", "store": "...", "unit": "kg", "history": { "2026-02-20": 4.99 } } }
            results = {}
            for row in rows:
                p_id, name, store, price, unit, date_str = row
                if p_id not in results:
                    results[p_id] = {
                        "id": p_id,
                        "name": name,
                        "store": store,
                        "unit": unit or "each",
                        "history": {}
                    }
                # Keep the latest price for that day if there are multiple entries
                if date_str not in results[p_id]["history"]:
                    results[p_id]["history"][date_str] = price
                    
            return list(results.values())
