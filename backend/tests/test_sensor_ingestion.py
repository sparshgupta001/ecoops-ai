from __future__ import annotations

from fastapi.testclient import TestClient

import backend.main as main
from backend.repositories.sensor_repository import SensorRepository
from backend.repositories.workflow_repository import WorkflowRepository
from backend.repositories.incident_repository import LocalIncidentRepository


def test_sensor_ingestion_valid_payload(monkeypatch, tmp_path):
    repo = SensorRepository(tmp_path / "sensors.json")
    monkeypatch.setattr(main, "sensor_repository", repo)
    client = TestClient(main.app)

    payload = {
        "sensor_id": "SEN-FLOOD-GATE-1",
        "source": "campus_iot_mesh",
        "location": "Gate 2 (Low Point)",
        "rainfall": 65.5,
        "water_level": 52.0,
        "forecast": "heavy",
        "timestamp": "2026-10-10T10:30:00Z",
        "drainage_capacity": 40.0,
        "drainage_blockage": 30.0,
        "metadata": {"battery_level": 94, "firmware": "v2.1"},
    }

    response = client.post("/api/sensors/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["sensor_id"] == "SEN-FLOOD-GATE-1"
    assert data["source"] == "campus_iot_mesh"
    assert data["location"] == "Gate 2 (Low Point)"
    assert data["rainfall"] == 65.5
    assert data["water_level"] == 52.0
    assert data["forecast"] == "heavy"
    assert data["timestamp"] == "2026-10-10T10:30:00Z"
    assert "ingested_at" in data
    assert data["id"].startswith("obs-")
    assert data["metadata"]["battery_level"] == 94

    # Check persistence
    stored = repo.list_observations()
    assert len(stored) == 1
    assert stored[0]["sensor_id"] == "SEN-FLOOD-GATE-1"


def test_sensor_ingestion_validation_errors(monkeypatch, tmp_path):
    repo = SensorRepository(tmp_path / "sensors.json")
    monkeypatch.setattr(main, "sensor_repository", repo)
    client = TestClient(main.app)

    # Missing sensor_id
    res1 = client.post("/api/sensors/ingest", json={"location": "Library", "rainfall": 20, "water_level": 10})
    assert res1.status_code == 422

    # Negative rainfall
    res2 = client.post(
        "/api/sensors/ingest",
        json={"sensor_id": "SEN-1", "location": "Library", "rainfall": -5.0, "water_level": 10},
    )
    assert res2.status_code == 422

    # Rainfall exceeds max boundary (200)
    res3 = client.post(
        "/api/sensors/ingest",
        json={"sensor_id": "SEN-1", "location": "Library", "rainfall": 250.0, "water_level": 10},
    )
    assert res3.status_code == 422


def test_monitor_endpoint_demo_fallback_when_empty(monkeypatch, tmp_path):
    sensor_repo = SensorRepository(tmp_path / "sensors.json")
    workflow_repo = WorkflowRepository(tmp_path / "workflows.json")
    incident_repo = LocalIncidentRepository(str(tmp_path / "incidents.json"))

    monkeypatch.setattr(main, "sensor_repository", sensor_repo)
    monkeypatch.setattr(main, "workflow_repository", workflow_repo)
    monkeypatch.setattr(main, "incident_repository", incident_repo)

    client = TestClient(main.app)
    response = client.get("/api/monitor")
    assert response.status_code == 200
    data = response.json()

    assert data["demo_mode"] is True
    assert "Demo Fallback" in data["source"]
    assert data["sensor_observation"] is None


def test_monitor_endpoint_switches_to_live_on_ingestion(monkeypatch, tmp_path):
    sensor_repo = SensorRepository(tmp_path / "sensors.json")
    workflow_repo = WorkflowRepository(tmp_path / "workflows.json")
    incident_repo = LocalIncidentRepository(str(tmp_path / "incidents.json"))

    monkeypatch.setattr(main, "sensor_repository", sensor_repo)
    monkeypatch.setattr(main, "workflow_repository", workflow_repo)
    monkeypatch.setattr(main, "incident_repository", incident_repo)

    client = TestClient(main.app)

    # Ingest a sensor reading
    client.post(
        "/api/sensors/ingest",
        json={
            "sensor_id": "SEN-STREAM-01",
            "source": "live_gateway",
            "location": "North Parking",
            "rainfall": 48.0,
            "water_level": 35.0,
        },
    )

    response = client.get("/api/monitor")
    assert response.status_code == 200
    data = response.json()

    assert data["demo_mode"] is False
    assert "SEN-STREAM-01" in data["source"]
    assert data["latest_readings"]["sensor_id"] == "SEN-STREAM-01"
    assert data["latest_readings"]["location"] == "North Parking"
    assert data["latest_readings"]["rainfall"] == 48.0
    assert data["latest_readings"]["water_level"] == 35.0
    assert data["sensor_observation"]["sensor_id"] == "SEN-STREAM-01"
    assert len(data["recent_sensor_observations"]) == 1
