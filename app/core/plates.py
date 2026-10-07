"""Indian vehicle registration plate validation."""

import re
from typing import Optional

# Standard series, e.g. "MH 12 QX 4821", "DL3CAB1234", "KA 01 A 0001"
_STANDARD = re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{4}$")
# Bharat series, e.g. "22 BH 1234 AA"
_BHARAT = re.compile(r"^\d{2}BH\d{4}[A-Z]{1,2}$")


def normalize_plate(plate_text: Optional[str]) -> Optional[str]:
    """Uppercase and strip spaces, dots and hyphens from plate text."""
    if not plate_text:
        return None
    return re.sub(r"[\s.\-]", "", plate_text).upper() or None


def is_valid_indian_plate(plate_text: Optional[str]) -> bool:
    """True if the plate text matches a standard or Bharat-series Indian format."""
    plate = normalize_plate(plate_text)
    if not plate:
        return False
    return bool(_STANDARD.match(plate) or _BHARAT.match(plate))
