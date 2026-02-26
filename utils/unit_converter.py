import re
from typing import Tuple, Optional

class UnitConverter:
    """Parses and standardizes units for grocery items."""
    
    # Common patterns: "4 kg", "907 g", "4 L", "1.5 lb", "1 bunch", "1 ea", "1 un"
    UNIT_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(kg|g|lb|l|ml|oz|units|count|pk|ea|bunch|roll|un)', re.IGNORECASE)
    # Unit price pattern: "65¢/100g", "$2.49/lb", "$0.99 / 1ea", "$1.99 /un."
    UNIT_PRICE_PATTERN = re.compile(r'(?:\$|\s)?(\d+(?:\.\d+)?)\s*(?:¢|c|\$)?\s*/\s*(\d+(?:\.\d+)?)?\s*(kg|g|lb|oz|l|ml|unit|ea|bunch|un)', re.IGNORECASE)

    @staticmethod
    def parse_quantity(text: str) -> Tuple[Optional[float], Optional[str]]:
        """Extracts quantity and unit from a string (e.g., '907 g')."""
        if not text:
            return None, None
        
        match = UnitConverter.UNIT_PATTERN.search(text)
        if match:
            quantity = float(match.group(1))
            unit = match.group(2).lower()
            return quantity, unit
        return None, None

    @staticmethod
    def parse_unit_price_string(text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Parses strings like '65¢/100g' -> (0.65, 100, 'g')"""
        if not text:
            return None, None, None
        
        match = UnitConverter.UNIT_PRICE_PATTERN.search(text)
        if match:
            val = float(match.group(1))
            # If it contains ¢ or c and no $, it's cents
            if ('¢' in text or 'c' in text.lower()) and '$' not in text:
                val = val / 100.0
            
            qty = float(match.group(2)) if match.group(2) else 1.0
            unit = match.group(3).lower()
            return val, qty, unit
        return None, None, None

    @staticmethod
    def to_standard_unit(price: float, quantity: float, unit: str) -> Tuple[float, str]:
        """
        Converts price/quantity to a standard unit price.
        Target units: 1kg for weight, 1L for volume, 1 unit for count.
        Returns (unit_price, standard_unit).
        """
        if not price or not quantity or not unit:
            return 0.0, "unknown"

        # Conversions to KG
        if unit == 'g':
            return (price / (quantity / 1000)), "kg"
        if unit == 'kg':
            return (price / quantity), "kg"
        if unit == 'lb':
            # 1 lb = 0.453592 kg
            return (price / (quantity * 0.453592)), "kg"
        if unit == 'oz':
            # 1 oz = 0.0283495 kg
            return (price / (quantity * 0.0283495)), "kg"

        if unit in ['ml', 'l']:
            # Conversions to L
            if unit == 'ml':
                return (price / (quantity / 1000)), "L"
            if unit == 'l':
                return (price / quantity), "L"

        # Default: Price per unit/count (ea, bunch, roll, unit, etc.)
        return (price / quantity), "unit"
