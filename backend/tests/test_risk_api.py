import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.models import AIInterpretation
from backend.services.ai_service import AIService
from backend.services.notification_service import NotificationService
from backend.services.risk_service import calculate_risk
from rag.retriever import LocalRetriever


def test_risk_calculation_thresholds():
    low = calculate_risk({"rainfall": 10, "water_level": 15, "location": "Block A"})
    assert low["severity"] == "LOW"

    high = calculate_risk({"rainfall": 85, "water_level": 30, "location": "Block C"})
    assert high["severity"] == "HIGH"

    critical = calculate_risk({"rainfall": 105, "water_level": 95, "location": "Block D"})
    assert critical["severity"] == "CRITICAL"


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_endpoint():
    client = TestClient(app)
    payload = {"location": "Block C", "rainfall": 82, "water_level": 74, "forecast": "heavy"}
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_type"] == "waterlogging"
    assert data["location"] == "Block C"
    assert data["severity"] in {"HIGH", "CRITICAL"}


def test_invalid_environmental_input():
    client = TestClient(app)
    response = client.post("/api/analyze", json={"location": "Block C", "rainfall": -5, "water_level": 50})
    assert response.status_code == 422


def test_ai_mode_selection(monkeypatch):
    monkeypatch.setenv("AWS_AI_ENABLED", "false")
    service = AIService()
    result = service.generate_response({"location": "Block C", "rainfall": 82, "water_level": 74}, {"severity": "HIGH"})
    assert result["source"] == "mock"

    monkeypatch.setenv("AWS_AI_ENABLED", "true")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_BEDROCK_MODEL_ID", "test-model")

    class FakeBody:
        def read(self):
            return json.dumps({
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "risk_explanation": "High waterlogging risk detected.",
                        "affected_areas": ["Block C"],
                        "recommended_actions": ["Inspect drains"],
                        "priority": "HIGH",
                        "evidence": [{"source": "campus_emergency_sop.txt", "excerpt": "Close unsafe access points."}],
                    })
                }]
            }).encode()

    class FakeClient:
        def invoke_model(self, **kwargs):
            return {"body": FakeBody()}

    with patch("boto3.client", return_value=FakeClient()):
        service = AIService()
        retrieved_evidence = [{"source": "verified-campus-doc.txt", "excerpt": "Recorded drainage guidance.", "relevance": 0.5}]
        result = service.generate_response(
            {"location": "Block C", "rainfall": 82, "water_level": 74},
            {"severity": "HIGH"},
            evidence=retrieved_evidence,
        )
        assert result["source"] == "bedrock"
        assert [item["source"] for item in result["evidence"]] == ["verified-campus-doc.txt"]
        AIInterpretation.model_validate(result)


def test_mock_ai_does_not_fabricate_evidence(monkeypatch):
    monkeypatch.setenv("AWS_AI_ENABLED", "false")
    result = AIService().generate_response(
        {"location": "Block C", "rainfall": 82, "water_level": 74},
        {"severity": "HIGH"},
        evidence=[],
    )
    assert result["source"] == "mock"
    assert result["evidence"] == []


def test_retrieval_and_source_attribution():
    retriever = LocalRetriever()
    results = retriever.retrieve("stormwater drainage and flood risk near Block C", top_k=3)
    assert results
    assert all("source" in item and "excerpt" in item for item in results)


def test_incident_approval_rejection():
    client = TestClient(app)
    payload = {"location": "Block C", "rainfall": 82, "water_level": 74, "forecast": "heavy"}
    response = client.post("/api/analyze", json=payload)
    incident_id = response.json()["incident"]["incident_id"]

    approved = client.post(f"/api/incidents/{incident_id}/approve", json={"approved": True, "reviewer": "demo"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    rejected = client.post(f"/api/incidents/{incident_id}/approve", json={"approved": False, "reviewer": "demo"})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_aws_disabled_fallback():
    service = NotificationService()
    assert service.enabled is False
    result = service.send_incident_alert({"location": "Block A", "severity": "HIGH"}, ["Inspect drains"])
    assert result["mode"] == "mock"
