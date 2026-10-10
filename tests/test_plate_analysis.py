"""Tests for vehicle plate detection, trigger conditions, and Indian registration plate analysis."""

from app.core.plates import (
    is_valid_indian_plate,
    is_car_or_bike,
    normalize_plate,
    analyze_plate_text,
    render_hsrp_badge_html,
)


def test_is_car_or_bike():
    """Verify only cars, bikes, and motorized transport trigger plate analysis."""
    # Positive: Cars and bikes
    assert is_car_or_bike("car") is True
    assert is_car_or_bike("motorcycle") is True
    assert is_car_or_bike("two-wheeler") is True
    assert is_car_or_bike("bike") is True
    assert is_car_or_bike("scooter") is True
    assert is_car_or_bike("auto-rickshaw") is True
    assert is_car_or_bike("Commercial delivery mini-truck") is True
    assert is_car_or_bike("SUV") is True

    # Negative: Pedestrians, walking, none
    assert is_car_or_bike("On foot / none") is False
    assert is_car_or_bike("pedestrian") is False
    assert is_car_or_bike("walking") is False
    assert is_car_or_bike("handcart") is False
    assert is_car_or_bike(None) is False
    assert is_car_or_bike("") is False


def test_standard_indian_plate_analysis():
    """Verify standard state series plates are properly parsed with state and RTO."""
    res = analyze_plate_text("MH 12 QX 4821")
    assert res["is_valid"] is True
    assert res["formatted"] == "MH 12 QX 4821"
    assert res["state_code"] == "MH"
    assert res["state_name"] == "Maharashtra"
    assert res["rto_code"] == "12"
    assert res["rto_district"] == "Pune (Central)"
    assert res["series"] == "QX"
    assert res["unique_number"] == "4821"
    assert "Maharashtra" in res["summary"]
    assert "Pune" in res["summary"]


def test_bharat_series_plate_analysis():
    """Verify Bharat (BH) pan-India series plates are properly parsed."""
    res = analyze_plate_text("22 BH 1234 AA")
    assert res["is_valid"] is True
    assert res["formatted"] == "22 BH 1234 AA"
    assert res["state_code"] == "BH"
    assert "Bharat" in res["state_name"]
    assert res["unique_number"] == "1234"


def test_invalid_or_partial_plate_analysis():
    """Verify partial or non-standard plates return safe diagnostics without breaking."""
    res = analyze_plate_text("MH 12")
    assert res["is_valid"] is False
    assert "Unusual or partial format" in res["summary"]

    empty = analyze_plate_text(None)
    assert empty["is_valid"] is False
    assert empty["formatted"] == "Not legible"


def test_hsrp_badge_rendering():
    """Verify authentic HSRP HTML badge renders with IND identifier."""
    html = render_hsrp_badge_html("MH 12 QX 4821")
    assert "IND" in html
    assert "MH 12 QX 4821" in html
