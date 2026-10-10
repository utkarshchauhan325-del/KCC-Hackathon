"""Tests for the TinyFish-powered Mutha river watch (agent calls are mocked)."""

from datetime import date
from unittest import mock

from app.core import river_watch
from app.core.scoring import project_overflow
from app.core.tinyfish_client import run_web_agent

TODAY = date(2026, 10, 11)


def test_release_bands():
    assert river_watch.release_band(None)["label"] == "No release"
    assert river_watch.release_band(0)["level"] == "Low"
    assert river_watch.release_band(2000)["label"] == "Release on"
    assert river_watch.release_band(9372)["level"] == "High"
    assert river_watch.release_band(40000)["level"] == "Critical"


def test_old_release_is_not_current():
    s = river_watch.summarise_reports([
        {"date": "2026-07-25", "discharge_cusecs": 9372, "headline": "Khadakwasla increases discharge"},
        {"date": "2026-10-10", "discharge_cusecs": None, "headline": "Khadakwasla storage update"},
    ], TODAY)
    assert s["latest"]["discharge_cusecs"] == 9372
    assert s["current"] is False
    assert s["current_cusecs"] == 0.0 and s["inflow_pct_per_hour"] == 0.0
    assert s["reports"][0]["date"] == "2026-10-10"  # newest first


def test_recent_release_is_current_and_adds_inflow():
    s = river_watch.summarise_reports([{"date": "2026-10-10", "discharge_cusecs": "12000", "headline": "Mutha alert"}], TODAY)
    assert s["current"] is True
    assert s["band"]["label"] == "Riverbank alert"
    assert s["inflow_pct_per_hour"] == 4.8


def test_bad_rows_are_dropped():
    s = river_watch.summarise_reports([
        {"date": "not a date", "discharge_cusecs": 5000, "headline": "Khadakwasla"},
        {"date": "2027-01-01", "discharge_cusecs": 5000, "headline": "Khadakwasla"},  # future
        {"date": "2026-10-09", "discharge_cusecs": "lots", "headline": "Khadakwasla"},
    ], TODAY)
    assert len(s["reports"]) == 1 and s["reports"][0]["discharge_cusecs"] is None
    assert s["latest"] is None


def test_release_raises_riverside_overflow():
    dry = [0.0] * 24
    calm = project_overflow(60, 40, "River Discharge Outfall", dry)
    released = project_overflow(60, 40, "River Discharge Outfall", dry, river_inflow_pct_per_h=4.8)
    assert calm["overflow_eta_h"] is None
    assert released["overflow_eta_h"] is not None
    assert released["projected_peak_pct"] > calm["projected_peak_pct"]


def test_refresh_caches_result_and_keeps_old_data_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(river_watch, "CACHE_PATH", tmp_path / "river_watch.json")
    ok = {"status": "ok", "steps": ["Read results"], "run_id": "r1",
          "result": {"reports": [{"date": "2026-10-10", "discharge_cusecs": 3000, "headline": "Khadakwasla release"}]}}
    with mock.patch.object(river_watch, "run_web_agent", return_value=ok):
        w = river_watch.refresh_river_watch()
    assert w["status"] == "ok" and w["latest"]["discharge_cusecs"] == 3000

    failed = {"status": "network_error", "error": "timed out", "steps": []}
    with mock.patch.object(river_watch, "run_web_agent", return_value=failed):
        w = river_watch.refresh_river_watch()
    assert w["status"] == "network_error"
    assert w["latest"]["discharge_cusecs"] == 3000  # previous reading kept


def test_get_river_watch_without_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(river_watch, "CACHE_PATH", tmp_path / "missing.json")
    w = river_watch.get_river_watch()
    assert w["status"] == "never_run" and w["latest"] is None and w["inflow_pct_per_hour"] == 0.0


def test_run_web_agent_parses_event_stream(monkeypatch):
    monkeypatch.setenv("TINYFISH_API_KEY", "sk-test")
    lines = [
        'data: {"type":"STARTED","run_id":"r9"}',
        'data: {"type":"PROGRESS","run_id":"r9","purpose":"Visit page"}',
        'data: {"type":"COMPLETE","run_id":"r9","status":"COMPLETED","result":{"reports":[]}}',
    ]
    resp = mock.MagicMock(status_code=200)
    resp.iter_lines.return_value = lines
    resp.__enter__.return_value = resp
    with mock.patch("app.core.tinyfish_client.requests.post", return_value=resp):
        out = run_web_agent("https://example.com", "goal")
    assert out == {"status": "ok", "result": {"reports": []}, "steps": ["Visit page"], "run_id": "r9"}


def test_run_web_agent_without_key(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    monkeypatch.delenv("tinyfishapikey", raising=False)
    with mock.patch("app.core.tinyfish_client.settings") as s:
        s.TINYFISH_API_KEY = ""
        assert run_web_agent("https://example.com", "goal")["status"] == "missing_key"


def test_other_rivers_are_ignored():
    s = river_watch.summarise_reports([
        {"date": "2026-10-10", "discharge_cusecs": 9400, "headline": "Mukkombu dam releases 9,400 cusecs into Cauvery"},
        {"date": "2026-08-02", "discharge_cusecs": 20779, "headline": "Khadakwasla releases 20,779 cusecs into Mutha"},
    ], TODAY)
    assert [r["discharge_cusecs"] for r in s["reports"]] == [20779]
    assert s["current"] is False
