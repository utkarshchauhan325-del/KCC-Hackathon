from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_priority_queue_page():
    response = client.get("/priority-queue")
    assert response.status_code == 200
    assert "Priority Queue" in response.text
    assert "CivicEye" in response.text

def test_root_redirect():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "/priority-queue" in response.headers.get("location", "")

def test_get_stats():
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "open_incidents" in data
    assert "analyzed_frames_per_hr" in data
    assert "pending_violations" in data
    assert "active_crews" in data

def test_get_incidents():
    response = client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        first = data[0]
        assert "id" in first
        assert "risk_score" in first
        assert "location" in first

def test_get_cameras():
    response = client.get("/api/v1/cameras")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_dispatch_and_resolve_api():
    # Test dispatching
    res = client.post("/api/v1/dispatch", json={
        "incident_id": "test_mock_1",
        "team_name": "Rapid Response Bravo",
        "notes": "Fast verification test"
    })
    assert res.status_code == 200
    assert res.json().get("status") == "DISPATCHED"

    # Test resolving
    res_resolve = client.post("/api/v1/resolve", json={
        "incident_id": "test_mock_1",
        "notes": "Verified resolved in test"
    })
    assert res_resolve.status_code == 200
    assert res_resolve.json().get("status") == "RESOLVED"
