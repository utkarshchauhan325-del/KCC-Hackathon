"""Indian vehicle registration plate validation and analysis."""

import re
from html import escape
from typing import Any, Dict, Optional

# Standard series, e.g. "MH 12 QX 4821", "DL3CAB1234", "KA 01 A 0001"
_STANDARD = re.compile(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{4})$")
# Bharat series, e.g. "22 BH 1234 AA"
_BHARAT = re.compile(r"^(\d{2})BH(\d{4})([A-Z]{1,2})$")

INDIAN_STATES: Dict[str, str] = {
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "DD": "Daman and Diu",
    "DL": "Delhi",
    "DN": "Dadra and Nagar Haveli",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HP": "Himachal Pradesh",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "JK": "Jammu and Kashmir",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "TS": "Telangana",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "WB": "West Bengal",
}

MAHARASHTRA_RTOS: Dict[str, str] = {
    "01": "Mumbai (South)",
    "02": "Mumbai (West)",
    "03": "Mumbai (East)",
    "04": "Thane",
    "05": "Kalyan",
    "06": "Raigad (Pen)",
    "07": "Sindhudurg",
    "08": "Ratnagiri",
    "09": "Kolhapur",
    "10": "Sangli",
    "11": "Satara",
    "12": "Pune (Central)",
    "13": "Solapur",
    "14": "Pimpri-Chinchwad (PCMC)",
    "15": "Nashik",
    "16": "Ahmednagar",
    "17": "Shrirampur",
    "18": "Dhule",
    "19": "Jalgaon",
    "20": "Chhatrapati Sambhajinagar",
    "21": "Jalna",
    "22": "Parbhani",
    "23": "Beed",
    "24": "Latur",
    "25": "Dharashiv (Osmanabad)",
    "26": "Nanded",
    "27": "Amravati",
    "28": "Buldhana",
    "29": "Yavatmal",
    "30": "Akola",
    "31": "Nagpur (Urban)",
    "32": "Wardha",
    "33": "Gadchiroli",
    "34": "Chandrapur",
    "35": "Gondia",
    "36": "Bhandara",
    "37": "Washim",
    "38": "Hingoli",
    "39": "Nandurbar",
    "40": "Nagpur (Rural)",
    "41": "Malegaon",
    "42": "Baramati",
    "43": "Navi Mumbai (Vashi)",
    "46": "Navi Mumbai (Panvel)",
    "47": "Borivali (Mumbai North)",
    "48": "Vasai-Virar",
    "49": "Nagpur (East)",
    "50": "Karad",
    "51": "Nashik (Rural)",
    "52": "Parbhani (Rural)",
    "53": "Phaltan",
    "54": "Baramati (South)",
    "55": "Akluj",
}


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


def is_car_or_bike(vehicle_type: Optional[str]) -> bool:
    """True if vehicle_type represents a car, motorcycle, bike, or other motorized road vehicle."""
    if not vehicle_type:
        return False
    val = vehicle_type.strip().lower()
    if val in {"none", "null", "on foot", "pedestrian", "walking", "handcart", "cart"}:
        return False
    keywords = [
        "car", "bike", "motorcycle", "scooter", "two-wheeler", "2-wheeler",
        "auto", "rickshaw", "auto-rickshaw", "truck", "tempo", "van", "suv",
        "vehicle", "lorry", "bus", "jeep"
    ]
    return any(k in val for k in keywords)


def analyze_plate_text(plate_text: Optional[str]) -> Dict[str, Any]:
    """Perform structured analysis of the number plate characters.
    
    Returns breakdown of state, RTO district, registration series, number, and validity.
    """
    clean = normalize_plate(plate_text)
    if not clean:
        return {
            "is_valid": False,
            "raw_text": plate_text or "",
            "formatted": "Not legible",
            "state_code": None,
            "state_name": "Unknown",
            "rto_code": None,
            "rto_district": "Unknown",
            "series": None,
            "unique_number": None,
            "format_type": "Not legible",
            "summary": "Plate characters could not be discerned from footage.",
        }

    # 1. Standard Indian State Series
    m_std = _STANDARD.match(clean)
    if m_std:
        st, rto, ser, num = m_std.groups()
        rto_padded = rto.zfill(2)
        formatted = f"{st} {rto_padded} {ser} {num}" if ser else f"{st} {rto_padded} {num}"
        state_name = INDIAN_STATES.get(st, f"State ({st})")
        
        district_name = f"RTO Code {rto_padded}"
        if st == "MH":
            district_name = MAHARASHTRA_RTOS.get(rto_padded, f"Maharashtra RTO {rto_padded}")
        elif st == "DL":
            district_name = f"Delhi Transport Authority Zone {rto_padded}"

        return {
            "is_valid": True,
            "raw_text": plate_text,
            "formatted": formatted,
            "state_code": st,
            "state_name": state_name,
            "rto_code": rto_padded,
            "rto_district": district_name,
            "series": ser or "Standard",
            "unique_number": num,
            "format_type": "Standard State Registration (MoRTH)",
            "summary": (
                f"Registered in {state_name} under {district_name}. "
                f"Series code '{ser or 'Standard'}', vehicle number '{num}'."
            ),
        }

    # 2. Bharat (BH) Pan-India Series
    m_bh = _BHARAT.match(clean)
    if m_bh:
        yr, num, ser = m_bh.groups()
        formatted = f"{yr} BH {num} {ser}"
        return {
            "is_valid": True,
            "raw_text": plate_text,
            "formatted": formatted,
            "state_code": "BH",
            "state_name": "Bharat Series (Pan-India MoRTH)",
            "rto_code": "BH",
            "rto_district": "All-India Transport Registration",
            "series": ser,
            "unique_number": num,
            "format_type": "Bharat (BH) Non-Localized Series",
            "summary": f"Pan-India Bharat Series (Year 20{yr}). Registration number '{num} {ser}'.",
        }

    # 3. Partial or Non-Standard Format
    st_guess = clean[:2] if len(clean) >= 2 and clean[:2].isalpha() else None
    state_name = INDIAN_STATES.get(st_guess, "Unverified") if st_guess else "Unverified"
    return {
        "is_valid": False,
        "raw_text": plate_text,
        "formatted": clean,
        "state_code": st_guess,
        "state_name": state_name,
        "rto_code": None,
        "rto_district": "Unverified",
        "series": None,
        "unique_number": None,
        "format_type": "Non-standard / Partial Format",
        "summary": f"Detected characters: '{clean}'. Unusual or partial format; manual officer verification required.",
    }


def render_hsrp_badge_html(plate_text: Optional[str]) -> str:
    """Render an authentic Indian High Security Registration Plate (HSRP) graphic badge."""
    analysis = analyze_plate_text(plate_text)
    display_text = escape(analysis["formatted"] if analysis["is_valid"] else (plate_text or "NOT LEGIBLE"))
    return f"""
    <div style="display:inline-flex;align-items:center;background:#FFFFFF;border:2px solid #0F172A;border-radius:6px;overflow:hidden;box-shadow:0 3px 8px rgba(0,0,0,0.12);font-family:'DIN Next', 'Arial Black', Impact, sans-serif;letter-spacing:1.5px;max-width:fit-content;margin:6px 0;">
      <div style="background:#0284C7;color:#FFFFFF;padding:6px 7px;font-size:10px;font-weight:900;display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1;border-right:1.5px solid #0369A1;">
        <span style="font-size:11px;">🇮🇳</span>
        <span style="font-size:8px;margin-top:2px;letter-spacing:0.5px;">IND</span>
      </div>
      <div style="padding:6px 14px;font-size:18px;font-weight:800;color:#0F172A;text-transform:uppercase;white-space:nowrap;">
        {display_text}
      </div>
    </div>
    """
