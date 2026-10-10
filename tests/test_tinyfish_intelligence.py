"""Unit tests for TinyFish Civic Intelligence integration."""

from unittest.mock import MagicMock, patch
import pytest

from app.core.tinyfish_client import (
    assess_severity,
    categorize_report,
    execute_tinyfish_search,
    extract_pune_locations,
    fetch_pune_civic_intelligence,
    get_tinyfish_api_key,
    mask_api_key,
)


def test_mask_api_key():
    assert mask_api_key("") == "Not Configured"
    assert mask_api_key("shortkey") == "sk-tinyfish-••••"
    masked = mask_api_key("sk-tinyfish-22MIoiBUrc5uAYdvDQ__BIbV_FAGdSuG")
    assert masked.startswith("sk-tinyfish")
    assert masked.endswith("SuG")
    assert "22MIoiBU" not in masked


def test_extract_pune_locations():
    text = "Severe waterlogging on Sinhagad Road and near Deccan Gymkhana due to heavy rains."
    locs = extract_pune_locations(text)
    assert "Sinhagad Road" in locs or "Sinhgad Road" in locs
    assert "Deccan Gymkhana" in locs or "Deccan" in locs

    text_none = "Global rainfall update across the northern hemisphere."
    assert extract_pune_locations(text_none) == []


def test_categorize_report():
    assert categorize_report("Traffic diversion", "Submerged road closed near Shivajinagar") == "Road Closure"
    assert categorize_report("PMC alert", "Emergency flood warning issued for riverside wards") == "Official Advisory"
    assert categorize_report("Nullah choke", "Stormwater drain blocked by garbage and silt") == "Drainage Issue"
    assert categorize_report("Resident grievance", "Citizen complaint regarding gutter overflow") == "Citizen Complaint"


def test_assess_severity():
    assert assess_severity("Dam discharge critical", "Water level crosses danger mark", "Official Advisory") == "Critical"
    assert assess_severity("Road closed", "Traffic completely blocked", "Road Closure") == "High"
    assert assess_severity("Weather outlook", "Moderate rain expected tomorrow", "Official Advisory") == "Medium"


@patch("requests.get")
def test_execute_tinyfish_search_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "query": "pune flood",
        "total_results": 1,
        "results": [
            {
                "title": "PMC Issues Flood Warning for Ekta Nagar",
                "snippet": "Residents advised to move vehicles due to waterlogging.",
                "url": "https://example.com/pune-alert",
                "date": "2 hours ago",
                "site_name": "punekarnews.in",
            }
        ],
    }
    mock_get.return_value = mock_resp

    with patch("app.core.tinyfish_client.get_tinyfish_api_key", return_value="sk-test-key-12345678"):
        result = execute_tinyfish_search("pune flood")
        assert result["status"] == "ok"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "PMC Issues Flood Warning for Ekta Nagar"


@patch("requests.get")
def test_execute_tinyfish_search_auth_error(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mock_get.return_value = mock_resp

    with patch("app.core.tinyfish_client.get_tinyfish_api_key", return_value="invalid_key"):
        result = execute_tinyfish_search("pune flood")
        assert result["status"] == "auth_error"
        assert "Invalid" in result["error"]
        assert result["results"] == []


def test_fetch_pune_civic_intelligence_fallback_when_no_key():
    with patch("app.core.tinyfish_client.get_tinyfish_api_key", return_value=""):
        data = fetch_pune_civic_intelligence(use_fallback_if_empty=True)
        assert data["status"] == "missing_key"
        assert data["source"] == "cached_fallback"
        assert len(data["reports"]) > 0
        assert data["counts"]["Total"] > 0
