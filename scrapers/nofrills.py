from bs4 import BeautifulSoup
from .base import BaseScraper
from typing import List, Dict, Optional
import json
import logging
import re

class NoFrillsScraper(BaseScraper):
    def parse(self, html: str) -> List[Dict[str, any]]:
        """Parses No Frills pages (PDP or Flyer)."""
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Detect if this is a PDP (Product Detail Page)
        if soup.find("h1", class_="product-name__item--name"):
            self.logger.info("Detected No Frills PDP (Individual Product Page)")
            res = self.parse_pdp(soup)
            if res:
                products.append(res)
            return products

        # Default to flyer/grid parsing
        cards = soup.find_all(class_="chakra-linkbox")
        self.logger.info(f"Detected {len(cards)} product cards using '.chakra-linkbox' selector.")
        
        for card in cards:
            try:
                brand_tag = card.find(attrs={"data-testid": "product-brand"})
                brand = brand_tag.get_text(strip=True) if brand_tag else ""
                
                title_tag = card.find(attrs={"data-testid": "product-title"})
                if not title_tag:
                    continue
                name = title_tag.get_text(strip=True)
                
                full_name = f"{brand} {name}".strip()
                
                price_blob = card.find(attrs={"data-testid": "price-product-tile"}) or \
                             card.find(attrs={"data-testid": "sale-price"}) or \
                             card.find(attrs={"data-testid": "regular-price"})
                
                if not price_blob:
                    continue
                
                price_text = price_blob.get_text(separator=' ', strip=True) 
                price = self._clean_price(price_text)
                
                package_tag = card.find(attrs={"data-testid": "product-package-size"})
                package_text = package_tag.get_text(strip=True) if package_tag else ""
                
                link_tag = card.find("a", class_="chakra-linkbox__overlay") or card.find("a")
                link = ""
                p_id = ""
                if link_tag and link_tag.get("href"):
                    href = link_tag.get("href")
                    link = "https://www.nofrills.ca" + href if href.startswith("/") else href
                    if "/p/" in link:
                        parts = link.split("/p/")
                        p_id = "nf-" + parts[1].split("?")[0]
                
                if price and name:
                    products.append({
                        "id": p_id or f"nf-auto-{hash(full_name)}",
                        "name": full_name,
                        "price": price,
                        "currency": "CAD",
                        "stock": "in_stock",
                        "unit_price_text": package_text,
                        "raw_weight": package_text,
                        "url": link,
                        "store": "nofrills",
                        "status": "success"
                    })
            except Exception as e:
                self.logger.debug(f"Skipping a card due to parsing error: {e}")
                continue
                
        return products

    def parse_pdp(self, soup: BeautifulSoup) -> Optional[Dict[str, any]]:
        """Parses an individual No Frills product detail page."""
        try:
            name_tag = soup.find("h1", class_="product-name__item--name")
            name = name_tag.get_text(strip=True) if name_tag else ""
            
            brand_tag = soup.find("span", class_="product-name__item--brand")
            brand = brand_tag.get_text(strip=True) if brand_tag else ""
            
            full_name = f"{brand} {name}".strip()
            
            price_tag = soup.find("span", class_="price__value") or \
                        soup.find(class_=re.compile(r"selling-price-list__item__price--(sale|now-price)__value"))
            
            price_text = price_tag.get_text(strip=True) if price_tag else ""
            price = self._clean_price(price_text)
            
            package_tag = soup.find("span", class_="product-name__item--package-size")
            package_text = package_tag.get_text(strip=True) if package_tag else ""
            
            unit_price_tag = soup.find("span", class_="price__unit")
            unit_price_text = unit_price_tag.get_text(strip=True) if unit_price_tag else ""

            # Check for comparison price list (standardized weights like $/kg)
            comparison_list = soup.find("ul", class_="comparison-price-list")
            if comparison_list:
                comp_items = comparison_list.find_all("li", class_="comparison-price-list__item")
                for comp_item in comp_items:
                    comp_text = comp_item.get_text(separator=" ", strip=True)
                    # Prioritize kg for standard unit
                    if "kg" in comp_text.lower():
                        unit_price_text = comp_text
                        break
                    elif "lb" in comp_text.lower() and not ("kg" in unit_price_text.lower()):
                        unit_price_text = comp_text

            if not name or not price:
                return None

            return {
                "name": full_name,
                "price": price,
                "currency": "CAD",
                "stock": "in_stock",
                "unit_price_text": unit_price_text if unit_price_text else package_text,
                "raw_weight": package_text,
                "store": "nofrills",
                "status": "success"
            }
        except Exception as e:
            self.logger.error(f"Error parsing No Frills PDP: {e}")
            return None

    def run_flyer(self, url: str, browser_mgr=None) -> List[Dict[str, any]]:
        """Specific run method for the flyer using JS injection."""
        if not browser_mgr:
            self.logger.error("NoFrills flyer extraction requires a browser manager.")
            return []

        js_script = """
        () => {
            const products = [];
            const cards = document.querySelectorAll('.chakra-linkbox');
            
            cards.forEach(card => {
                try {
                    const brand = card.querySelector('[data-testid="product-brand"]')?.innerText || "";
                    const title = card.querySelector('[data-testid="product-title"]')?.innerText || "";
                    if (!title) return;

                    const priceEl = card.querySelector('[data-testid="price-product-tile"]') || 
                                    card.querySelector('[data-testid="sale-price"]') || 
                                    card.querySelector('[data-testid="regular-price"]');
                    
                    const priceText = priceEl ? priceEl.innerText : "";
                    const packageText = card.querySelector('[data-testid="product-package-size"]')?.innerText || "";
                    
                    const linkEl = card.querySelector('a.chakra-linkbox__overlay') || card.querySelector('a');
                    const link = linkEl ? (linkEl.href.startsWith('/') ? 'https://www.nofrills.ca' + linkEl.href : linkEl.href) : "";
                    
                    let pId = "";
                    if (link.includes('/p/')) {
                        pId = link.split('/p/')[1].split('?')[0];
                    }

                    products.push({
                        "id": "nf-" + (pId || Math.random().toString(36).substring(7)),
                        "name": (brand + " " + title).trim(),
                        "price_raw": priceText,
                        "unit_price_text": packageText,
                        "url": link
                    });
                } catch (e) {}
            });
            return products;
        }
        """

        results = browser_mgr.execute_script(url, js_script)
        
        final_products = []
        if results:
            self.logger.info(f"JS extracted {len(results)} items from No Frills.")
            for res in results:
                price = self._clean_price(res["price_raw"])
                if price:
                    final_products.append({
                        "id": res["id"],
                        "name": res["name"],
                        "price": price,
                        "currency": "CAD",
                        "stock": "in_stock",
                        "unit_price_text": res["unit_price_text"],
                        "raw_weight": res["unit_price_text"],
                        "url": res["url"],
                        "store": "nofrills",
                        "status": "success"
                    })
        
        return final_products
