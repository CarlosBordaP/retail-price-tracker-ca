from bs4 import BeautifulSoup
from .base import BaseScraper
from typing import List, Dict, Optional
import logging
import re

class FoodBasicsScraper(BaseScraper):
    def parse(self, html: str) -> List[Dict[str, any]]:
        """Parses a Food Basics product page."""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # 1. Product Name
            name_tag = soup.select_one("h1.pi--title")
            name = name_tag.get_text(strip=True) if name_tag else ""
            
            # 2. Package Size / Weight
            weight_tag = soup.select_one("div.pi--weight")
            weight_text = weight_tag.get_text(strip=True) if weight_tag else ""
            
            # 3. Price
            price_tag = soup.select_one("span.price-update")
            price_text = price_tag.get_text(strip=True) if price_tag else ""
            price = self._clean_price(price_text)
            
            # 4. Unit Price
            # Food Basics often has the unit price ($/kg) near the main price
            unit_text = ""
            # Metro and Food Basics use pricing__secondary-price within pi--prices
            secondary_price_tag = soup.select_one(".pricing__secondary-price")
            if secondary_price_tag:
                unit_text = secondary_price_tag.get_text(separator=" ", strip=True)
            else:
                # Fallback to search in several likely containers
                price_container = soup.select_one("div.pi--price") or soup.select_one("div.pi--prices") or soup.select_one(".product-details__product-info__price")
                if price_container:
                    # Get all text and look for $/unit patterns
                    full_text = price_container.get_text(separator=" ", strip=True)
                    # If the unit price is present, it often follows a '/'
                    if "/" in full_text:
                        parts = full_text.split("/")
                        if len(parts) > 1:
                            # Reconstruct the unit price part (e.g., "$16.51 /kg")
                            # Usually it's the part that contains '$' and a unit
                            unit_match = re.search(r'\$?[\d,.]+\s*/\s*(?:kg|lb|l|ml|unit|ea|un)', full_text, re.IGNORECASE)
                            if unit_match:
                                unit_text = unit_match.group(0)
                    
                    # Fallback: if we didn't find a specific match but have a container, just clean it
                    if not unit_text:
                        unit_text = full_text.replace(price_text, "").strip()

            if not name or not price:
                self.logger.warning("Essential data missing for Food Basics product")
                return []

            return [{
                "name": name,
                "price": price,
                "currency": "CAD",
                "stock": "in_stock",
                "unit_price_text": f"{weight_text}, {unit_text}".strip(", "),
                "raw_weight": weight_text,
                "store": "foodbasics",
                "status": "success"
            }]
        except Exception as e:
            self.logger.error(f"Error parsing Food Basics: {e}")
            return []
