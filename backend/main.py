from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agents.impact_agent import assess_impact
from agents.response_agent import build_response_plan
from backend.config import BASE_DIR, settings
from backend.models import (
    AnalyticsResponse,
    EnvironmentalInput,
    ExecutionTraceRecord,
    IncidentApprovalRequest,
    IncidentRecord,
    KnowledgeResponse,
    MonitorResponse,
    ScenarioSimulationResult,
    TaskStatusUpdate,
)
from backend.repositories.incident_repository import incident_repository
from backend.repositories.workflow_repository import workflow_repository
from backend.services.ai_service import ai_service
from backend.services.notification_service import notification_service
from backend.services.risk_service import calculate_risk
from rag.retriever import retriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ecoops_ai")

app = FastAPI(title="EcoOps AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_incident(
    payload: dict[str, Any],
    assessment: dict[str, Any],
    ai_summary: dict[str, Any] | None = None,
    response_plan: dict[str, Any] | None = None,
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    status = "pending_approval" if assessment["severity"] in {"HIGH", "CRITICAL"} else "open"
    actions = (response_plan or {}).get("recommended_actions", [])
    incident = {
        "incident_id": f"INC-{uuid.uuid4().hex[:8].upper()}",
        "location": payload.get("location", "Unknown Location"),
        "risk_type": assessment["risk_type"],
        "severity": assessment["severity"],
        "probability": assessment["probability"],
        "environmental_data": payload,
        "timestamp": timestamp,
        "status": status,
        "response_plan": response_plan or {},
        "ai_summary": ai_summary or {},
        "execution_id": (execution or {}).get("execution_id"),
        "tasks": [
            {
                "task_id": uuid.uuid4().hex[:10],
                "title": action,
                "status": "planned",
                "created_at": timestamp,
                "updated_at": timestamp,
                "history": [{"status": "planned", "timestamp": timestamp}],
            }
            for action in actions
        ],
        "audit_events": [{"event": "incident_detected", "timestamp": timestamp, "actor": "system"}],
    }
    saved = incident_repository.create_incident(incident)
    logger.info(
        "incident_created",
        extra={
            "incident_id": saved["incident_id"],
            "location": saved["location"],
            "severity": saved["severity"],
            "timestamp": saved["timestamp"],
            "processing_stage": "incident_creation",
        },
    )
    return saved


def _record_stage(
    execution: dict[str, Any],
    stage: str,
    stage_input: dict[str, Any],
    operation: Any,
) -> Any:
    started_at = datetime.now(timezone.utc).isoformat()
    record = {
        "stage": stage,
        "status": "running",
        "started_at": started_at,
        "completed_at": None,
        "input": stage_input,
        "output": None,
        "evidence_references": [],
        "error": None,
    }
    execution["stages"].append(record)
    workflow_repository.save_execution(execution)
    try:
        output = operation()
        record["status"] = "completed"
        record["output"] = output
        if stage == "knowledge_retrieval":
            record["evidence_references"] = [item.get("source") for item in output]
        record["completed_at"] = datetime.now(timezone.utc).isoformat()
        return output
    except Exception as exc:
        record["status"] = "failed"
        record["error"] = str(exc)
        record["completed_at"] = datetime.now(timezone.utc).isoformat()
        execution["status"] = "failed"
        workflow_repository.save_execution(execution)
        raise
    finally:
        workflow_repository.save_execution(execution)


def _new_execution(environmental_data: dict[str, Any]) -> dict[str, Any]:
    execution = {
        "execution_id": f"EXE-{uuid.uuid4().hex[:10].upper()}",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "status": "running",
        "orchestration": "sequential_python_workflow",
        "ai_mode": "bedrock" if ai_service.enabled else "mock",
        "input": environmental_data,
        "stages": [],
    }
    workflow_repository.save_execution(execution)
    return execution


def analyze_environmental_data(payload: dict[str, Any] | EnvironmentalInput) -> dict[str, Any]:
    if not isinstance(payload, EnvironmentalInput):
        payload = EnvironmentalInput(**payload)

    environmental_data = payload.model_dump(exclude_none=True)
    execution = _new_execution(environmental_data)
    assessment = _record_stage(
        execution,
        "risk_assessment",
        environmental_data,
        lambda: calculate_risk(environmental_data),
    )
    impact = _record_stage(
        execution,
        "impact_analysis",
        {"risk_assessment": assessment, "environmental_data": environmental_data},
        lambda: assess_impact(assessment, environmental_data),
    )
    evidence = _record_stage(
        execution,
        "knowledge_retrieval",
        {"query_location": environmental_data.get("location"), "top_k": 3},
        lambda: retriever.retrieve(
            f"{environmental_data.get('location', '')} waterlogging flooding drainage route safety",
            top_k=3,
        ),
    )

    def plan_response() -> dict[str, Any]:
        plan = build_response_plan(assessment, impact)
        interpretation = ai_service.generate_response(
            environmental_data,
            assessment,
            context=["drainage map", "emergency SOP"],
            evidence=evidence,
        )
        return {"response_plan": plan, "ai_interpretation": interpretation}

    planning = _record_stage(
        execution,
        "response_planning",
        {"risk_assessment": assessment, "impact_analysis": impact, "evidence_count": len(evidence)},
        plan_response,
    )
    response_plan = planning["response_plan"]
    ai_summary = planning["ai_interpretation"]

    incident = None
    if assessment["severity"] in {"HIGH", "CRITICAL"}:
        approval_stage = {
            "stage": "human_approval",
            "status": "awaiting_approval",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "input": {"required": True, "severity": assessment["severity"]},
            "output": {"decision": None},
            "evidence_references": [],
            "error": None,
        }
        execution["stages"].append(approval_stage)
        execution["stages"].append({
            "stage": "notification",
            "status": "awaiting_approval",
            "started_at": None,
            "completed_at": None,
            "input": {"approval_required": True},
            "output": None,
            "evidence_references": [],
            "error": None,
        })
        incident = create_incident(
            environmental_data,
            assessment,
            ai_summary=ai_summary,
            response_plan=response_plan,
            execution=execution,
        )
        approval_stage["output"] = {"incident_id": incident["incident_id"], "decision": None}
    else:
        execution["stages"].extend([
            {
                "stage": "human_approval",
                "status": "not_required",
                "started_at": None,
                "completed_at": None,
                "input": {"required": False, "severity": assessment["severity"]},
                "output": None,
                "evidence_references": [],
                "error": None,
            },
            {
                "stage": "notification",
                "status": "not_required",
                "started_at": None,
                "completed_at": None,
                "input": {"approval_required": False},
                "output": None,
                "evidence_references": [],
                "error": None,
            },
        ])

    execution["status"] = "awaiting_approval" if incident else "completed"
    execution["completed_at"] = datetime.now(timezone.utc).isoformat()
    execution["incident_id"] = incident["incident_id"] if incident else None
    workflow_repository.save_execution(execution)
    if incident:
        incident["execution_trace"] = execution
        incident_repository.update_incident(incident["incident_id"], incident)

    logger.info(
        "risk_analysis_complete",
        extra={
            "incident_id": incident["incident_id"] if incident else "N/A",
            "location": assessment["location"],
            "severity": assessment["severity"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_stage": "risk_analysis",
        },
    )

    return {
        "risk_type": assessment["risk_type"],
        "severity": assessment["severity"],
        "probability": assessment["probability"],
        "location": assessment["location"],
        "environmental_data": environmental_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": ai_summary.get("risk_explanation", ai_summary.get("summary", "No summary available.")),
        "impact": ai_summary.get("affected_areas", ai_summary.get("impact", [])),
        "recommended_actions": ai_summary["recommended_actions"],
        "priority": ai_summary["priority"],
        "source": ai_summary.get("source", "mock"),
        "evidence": ai_summary.get("evidence", []),
        "response_plan": response_plan,
        "incident": incident,
        "approval_status": incident.get("status") if incident else "not_required",
        "execution_id": execution["execution_id"],
        "execution_trace": execution,
        "demo_mode": True,
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "EcoOps AI"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "EcoOps AI backend is running"}


@app.post("/api/analyze")
def analyze(data: EnvironmentalInput) -> dict[str, Any]:
    try:
        return analyze_environmental_data(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/incidents")
def get_incidents() -> list[dict[str, Any]]:
    return incident_repository.list_incidents()


@app.get("/api/incidents/{incident_id}", response_model=IncidentRecord)
def get_incident(incident_id: str) -> dict[str, Any]:
    incident = incident_repository.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/api/monitor", response_model=MonitorResponse)
def get_monitor() -> dict[str, Any]:
    executions = sorted(workflow_repository.list_executions(), key=lambda item: item.get("started_at", ""), reverse=True)
    incidents = incident_repository.list_incidents()
    latest = executions[0] if executions else None
    return {
        "demo_mode": True,
        "source": "Local scenario inputs and stored investigation records; no connected live sensor feed",
        "data_freshness": latest.get("started_at") if latest else None,
        "latest_readings": (latest or {}).get("input"),
        "recent_executions": executions[:10],
        "incident_count": len(incidents),
    }


@app.post("/api/scenarios/simulate", response_model=ScenarioSimulationResult)
def simulate_scenario(data: EnvironmentalInput) -> dict[str, Any]:
    environmental_data = data.model_dump(exclude_none=True)
    assessment = calculate_risk(environmental_data)
    impact = assess_impact(assessment, environmental_data)
    plan = build_response_plan(assessment, impact)
    return {
        "simulation": True,
        "persisted": False,
        "external_actions": False,
        "input": environmental_data,
        "risk_assessment": assessment,
        "impact_analysis": impact,
        "response_plan": plan,
    }


@app.get("/api/executions", response_model=list[ExecutionTraceRecord])
def get_executions() -> list[dict[str, Any]]:
    return sorted(
        workflow_repository.list_executions(),
        key=lambda item: item.get("started_at", ""),
        reverse=True,
    )[:100]


@app.get("/api/executions/{execution_id}", response_model=ExecutionTraceRecord)
def get_execution(execution_id: str) -> dict[str, Any]:
    execution = workflow_repository.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@app.get("/api/knowledge", response_model=KnowledgeResponse)
def get_knowledge() -> dict[str, Any]:
    incidents = incident_repository.list_incidents()
    documents = []
    for path in sorted((BASE_DIR / "rag" / "documents").glob("*.txt")):
        text = path.read_text(encoding="utf-8").strip()
        used_by = []
        for incident in incidents:
            sources = [item.get("source") for item in incident.get("ai_summary", {}).get("evidence", [])]
            if path.name in sources:
                used_by.append({
                    "incident_id": incident.get("incident_id"),
                    "location": incident.get("location"),
                    "recommendations": incident.get("response_plan", {}).get("recommended_actions", []),
                })
        documents.append({
            "name": path.name,
            "type": path.suffix.lstrip(".").upper(),
            "excerpt": text[:1200],
            "verified_document": True,
            "used_by": used_by,
            "recommendation_mapping": "Incident-level evidence; not mapped to individual recommendations",
        })
    return {"demo_mode": True, "documents": documents}


@app.get("/api/analytics", response_model=AnalyticsResponse)
def get_analytics() -> dict[str, Any]:
    incidents = incident_repository.list_incidents()
    severity_counts: dict[str, int] = {key: 0 for key in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
    status_counts: dict[str, int] = {}
    by_day: dict[str, int] = {}
    task_total = 0
    task_completed = 0
    approval_seconds: list[float] = []
    approved = rejected = 0
    for incident in incidents:
        severity = incident.get("severity", "UNKNOWN")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        status = incident.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        timestamp = incident.get("timestamp")
        if timestamp:
            by_day[timestamp[:10]] = by_day.get(timestamp[:10], 0) + 1
        tasks = incident.get("tasks", [])
        task_total += len(tasks)
        task_completed += sum(1 for task in tasks if task.get("status") == "completed")
        approved += status == "approved"
        rejected += status == "rejected"
        approval_timestamp = incident.get("approval_timestamp")
        if timestamp and approval_timestamp:
            try:
                created = datetime.fromisoformat(timestamp)
                decided = datetime.fromisoformat(approval_timestamp)
                approval_seconds.append(max(0.0, (decided - created).total_seconds()))
            except ValueError:
                pass
    return {
        "demo_mode": True,
        "source": "Stored local incident and task records",
        "incident_total": len(incidents),
        "by_severity": severity_counts,
        "by_status": status_counts,
        "by_day": [{"date": day, "count": count} for day, count in sorted(by_day.items())],
        "approvals": {"approved": approved, "rejected": rejected, "pending": status_counts.get("pending_approval", 0)},
        "tasks": {"total": task_total, "completed": task_completed, "completion_rate": task_completed / task_total if task_total else None},
        "mean_detection_to_decision_seconds": sum(approval_seconds) / len(approval_seconds) if approval_seconds else None,
    }


@app.get("/api/analytics/incidents.csv")
def export_incidents_csv() -> StreamingResponse:
    stream = io.StringIO()
    fields = ["incident_id", "location", "severity", "status", "timestamp", "approval_timestamp", "task_count", "completed_task_count"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for incident in incident_repository.list_incidents():
        tasks = incident.get("tasks", [])
        writer.writerow({
            **{field: incident.get(field, "") for field in fields if field not in {"task_count", "completed_task_count"}},
            "task_count": len(tasks),
            "completed_task_count": sum(1 for task in tasks if task.get("status") == "completed"),
        })
    stream.seek(0)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ecoops-incidents.csv"},
    )


@app.post("/api/incidents/{incident_id}/approve", response_model=IncidentRecord)
def approve_incident(incident_id: str, decision: IncidentApprovalRequest) -> dict[str, Any]:
    incident = incident_repository.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident["status"] = "approved" if decision.approved else "rejected"
    incident["approval_notes"] = decision.notes
    incident["approval_reviewer"] = decision.reviewer
    timestamp = datetime.now(timezone.utc).isoformat()
    incident["approval_timestamp"] = timestamp
    incident.setdefault("audit_events", []).append({
        "event": "incident_approved" if decision.approved else "incident_rejected",
        "timestamp": timestamp,
        "actor": decision.reviewer,
        "notes": decision.notes,
    })

    updated = incident_repository.update_incident(incident_id, incident)
    execution = workflow_repository.get_execution(incident.get("execution_id", ""))
    if execution:
        approval_stage = next((item for item in execution.get("stages", []) if item.get("stage") == "human_approval"), None)
        notification_stage = next((item for item in execution.get("stages", []) if item.get("stage") == "notification"), None)
        if approval_stage:
            approval_stage.update({
                "status": "approved" if decision.approved else "rejected",
                "completed_at": timestamp,
                "output": {"decision": incident["status"], "reviewer": decision.reviewer, "notes": decision.notes},
            })
        if decision.approved:
            notification = notification_service.send_incident_alert(
                updated,
                updated.get("response_plan", {}).get("recommended_actions", []),
            )
            if notification_stage:
                notification_stage.update({
                    "status": "completed" if notification.get("status") == "sent" else "simulated" if notification.get("status") == "simulated" else "failed",
                    "started_at": timestamp,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "output": notification,
                    "error": notification.get("error"),
                })
            incident.setdefault("audit_events", []).append({
                "event": "notification_" + notification.get("status", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": notification.get("mode"),
            })
            updated = incident_repository.update_incident(incident_id, incident)
        else:
            if notification_stage:
                notification_stage.update({"status": "not_required", "output": {"reason": "Incident rejected"}})
        execution["status"] = "completed"
        workflow_repository.save_execution(execution)
        incident["execution_trace"] = execution
        updated = incident_repository.update_incident(incident_id, incident)
    return updated


@app.patch("/api/incidents/{incident_id}/tasks/{task_id}", response_model=IncidentRecord)
def update_incident_task(incident_id: str, task_id: str, update: TaskStatusUpdate) -> dict[str, Any]:
    incident = incident_repository.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    task = next((item for item in incident.get("tasks", []) if item.get("task_id") == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if update.status in {"in_progress", "completed"} and incident.get("status") != "approved":
        raise HTTPException(status_code=409, detail="Incident approval is required before task execution")
    timestamp = datetime.now(timezone.utc).isoformat()
    task["status"] = update.status
    task["updated_at"] = timestamp
    task.setdefault("history", []).append({"status": update.status, "timestamp": timestamp, "note": update.note})
    incident.setdefault("audit_events", []).append({
        "event": "task_status_updated",
        "timestamp": timestamp,
        "actor": "operator",
        "task_id": task_id,
        "status": update.status,
        "notes": update.note,
    })
    return incident_repository.update_incident(incident_id, incident)


@app.post("/api/simulate")
async def simulate(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    default_payload = {
        "location": "Block C",
        "rainfall": 82,
        "water_level": 74,
        "forecast": "heavy",
    }
    request_payload = payload or default_payload
    return analyze_environmental_data(request_payload)
