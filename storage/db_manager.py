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
                datetime.utcnow().isoformat()
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
