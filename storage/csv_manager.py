import csv
import os
from datetime import datetime

class CSVManager:
    """Manages the dataset in CSV format."""
    
    def __init__(self, file_path="/Users/carlosborda/Documents/Python/Learning/scraping/data/price_dataset.csv"):
        self.file_path = file_path
        self._init_csv()

    def _init_csv(self):
        """Creates the CSV file with headers if it doesn't exist."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "date", 
                    "store", 
                    "product", 
                    "price", 
                    "unit", 
                    "quantity"
                ])

    def append_price(self, data: dict):
        """Appends a new price entry to the CSV file."""
        # We use the standardized unit price and unit as requested for the dataset
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("store", ""),
            data.get("product_name", ""),
            round(data.get("unit_price", 0.0), 2),
            data.get("standard_unit", ""),
            1.0 # Consistent with unit_price which is per 1 standard unit
        ]
        
        with open(self.file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
