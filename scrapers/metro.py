from bs4 import BeautifulSoup
from .base import BaseScraper
from typing import List, Dict, Optional
import logging
import re

class MetroScraper(BaseScraper):
    def parse(self, html: str) -> List[Dict[str, any]]:
        """Parses a Metro.ca product page."""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # 1. Product Name - Metro uses pi--title or product-details__title
            name_tag = soup.select_one("h1.pi--title") or soup.select_one("h1.product-details__title")
            name = name_tag.get_text(strip=True) if name_tag else ""
            
            # 2. Package Size / Weight
            weight_tag = soup.select_one("div.pi--weight")
            weight_text = weight_tag.get_text(strip=True) if weight_tag else ""
            
            # 3. Price
            price_tag = soup.select_one("span.price-update")
            price_text = price_tag.get_text(strip=True) if price_tag else ""
            price = self._clean_price(price_text)
            
            # 4. Unit Price
            # Metro uses pi--unit-price or pricing__secondary-price
            unit_tag = soup.select_one(".pi--unit-price") or soup.select_one(".pricing__secondary-price")
            unit_text = unit_tag.get_text(strip=True) if unit_tag else ""
            
            # If not found in specific tags, try the main price container
            if not unit_text:
                price_container = soup.select_one("div.pi--price") or soup.select_one(".product-details__product-info__price")
                if price_container:
                    full_text = price_container.get_text(separator=" ", strip=True)
                    unit_match = re.search(r'\$?[\d,.]+\s*/\s*(?:kg|lb|l|ml|unit|ea|un)', full_text, re.IGNORECASE)
                    if unit_match:
                        unit_text = unit_match.group(0)

            if not name or not price:
                self.logger.warning("Essential data missing for Metro product")
                # Debug: Log what was found
                self.logger.debug(f"Found name: {name}, price: {price}")
                return []

            return [{
                "name": name,
                "price": price,
                "currency": "CAD",
                "stock": "in_stock",
                "unit_price_text": f"{weight_text}, {unit_text}".strip(", "),
                "raw_weight": weight_text,
                "store": "metro",
                "status": "success"
            }]
        except Exception as e:
            self.logger.error(f"Error parsing Metro: {e}")
            return []
