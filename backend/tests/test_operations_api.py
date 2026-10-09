from fastapi.testclient import TestClient

import backend.main as main
from backend.repositories.incident_repository import IncidentRepository, LocalIncidentRepository
from backend.repositories.workflow_repository import WorkflowRepository
from backend.services.notification_service import NotificationService


def test_incident_repository_falls_back_to_local_when_dynamodb_fails(tmp_path):
    class FailedDynamoDB:
        def create_incident(self, incident):
            return None

        def update_incident(self, incident_id, incident):
            return None

        def get_incident(self, incident_id):
            return None

        def list_incidents(self):
            return []

    repository = IncidentRepository()
    repository._local = LocalIncidentRepository(str(tmp_path / "fallback.json"))
    repository._dynamodb = FailedDynamoDB()
    created = repository.create_incident({"incident_id": "INC-LOCAL", "status": "pending_approval"})
    updated = repository.update_incident("INC-LOCAL", {"incident_id": "INC-LOCAL", "status": "approved"})

    assert created["status"] == "pending_approval"
    assert updated["status"] == "approved"
    assert repository.get_incident("INC-LOCAL")["status"] == "approved"


def test_local_repository_repairs_duplicate_legacy_incident_ids(tmp_path):
    repository = LocalIncidentRepository(str(tmp_path / "duplicates.json"))
    repository.storage_path.write_text(
        '[{"incident_id":"INC-OLD","location":"Block C"},'
        '{"incident_id":"INC-OLD","location":"Gate 2"}]',
        encoding="utf-8",
    )

    incidents = repository.list_incidents()

    assert len(incidents) == 2
    assert incidents[0]["incident_id"] == "INC-OLD"
    assert incidents[1]["incident_id"] != "INC-OLD"
    assert {incident["location"] for incident in incidents} == {"Block C", "Gate 2"}


def test_scenario_endpoint_uses_drainage_inputs_without_creating_incidents(monkeypatch, tmp_path):
    incidents = LocalIncidentRepository(str(tmp_path / "incidents.json"))
    workflows = WorkflowRepository(tmp_path / "executions.json")
    monkeypatch.setattr(main, "incident_repository", incidents)
    monkeypatch.setattr(main, "workflow_repository", workflows)
    client = TestClient(main.app)

    response = client.post(
        "/api/scenarios/simulate",
        json={
            "location": "Block C",
            "rainfall": 70,
            "water_level": 45,
            "drainage_capacity": 100,
            "drainage_blockage": 0,
        },
    )
    blocked = client.post(
        "/api/scenarios/simulate",
        json={
            "location": "Block C",
            "rainfall": 70,
            "water_level": 45,
            "drainage_capacity": 0,
            "drainage_blockage": 100,
        },
    )
    forecast = client.post(
        "/api/scenarios/simulate",
        json={
            "location": "Block C",
            "rainfall": 70,
            "water_level": 60,
            "forecast": "extreme",
            "drainage_capacity": 100,
            "drainage_blockage": 0,
        },
    )

    assert response.status_code == blocked.status_code == forecast.status_code == 200
    assert response.json()["simulation"] is True
    assert response.json()["persisted"] is False
    assert response.json()["risk_assessment"]["severity"] == "MEDIUM"
    assert blocked.json()["risk_assessment"]["severity"] == "HIGH"
    assert forecast.json()["risk_assessment"]["severity"] == "HIGH"
    assert incidents.list_incidents() == []
    assert workflows.list_executions() == []


def test_execution_trace_approval_tasks_and_analytics(monkeypatch, tmp_path):
    incidents = LocalIncidentRepository(str(tmp_path / "incidents.json"))
    workflows = WorkflowRepository(tmp_path / "executions.json")
    monkeypatch.setattr(main, "incident_repository", incidents)
    monkeypatch.setattr(main, "workflow_repository", workflows)
    monkeypatch.setattr(main, "notification_service", NotificationService())
    client = TestClient(main.app)

    analyzed = client.post(
        "/api/analyze",
        json={"location": "Block C", "rainfall": 82, "water_level": 74, "forecast": "heavy"},
    )
    assert analyzed.status_code == 200
    payload = analyzed.json()
    assert [stage["stage"] for stage in payload["execution_trace"]["stages"]] == [
        "risk_assessment",
        "impact_analysis",
        "knowledge_retrieval",
        "response_planning",
        "human_approval",
        "notification",
    ]
    assert payload["execution_trace"]["orchestration"] == "sequential_python_workflow"
    assert payload["execution_trace"]["stages"][2]["evidence_references"]

    incident = payload["incident"]
    task = incident["tasks"][0]
    blocked_task = client.patch(
        f"/api/incidents/{incident['incident_id']}/tasks/{task['task_id']}",
        json={"status": "in_progress"},
    )
    assert blocked_task.status_code == 409

    approval = client.post(
        f"/api/incidents/{incident['incident_id']}/approve",
        json={"approved": True, "reviewer": "operator"},
    )
    assert approval.status_code == 200
    assert approval.json()["execution_trace"]["stages"][-1]["status"] == "simulated"
    task_update = client.patch(
        f"/api/incidents/{incident['incident_id']}/tasks/{task['task_id']}",
        json={"status": "completed", "note": "Inspection complete"},
    )
    assert task_update.status_code == 200
    assert task_update.json()["tasks"][0]["status"] == "completed"

    analytics = client.get("/api/analytics")
    assert analytics.status_code == 200
    assert analytics.json()["incident_total"] == 1
    assert analytics.json()["tasks"]["completion_rate"] == 1 / 3
    csv_response = client.get("/api/analytics/incidents.csv")
    assert "text/csv" in csv_response.headers["content-type"]
    assert "probability" not in csv_response.text.splitlines()[0]
    assert client.get("/api/knowledge").json()["documents"]