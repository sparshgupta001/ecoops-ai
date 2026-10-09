from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


class EnvironmentalInput(BaseModel):
    location: str = Field(..., min_length=2, max_length=120)
    rainfall: float = Field(..., ge=0, le=200)
    water_level: float = Field(..., ge=0, le=200)
    forecast: str = Field(default="normal")
    timestamp: datetime | None = None
    drainage_capacity: float | None = Field(default=None, ge=0, le=100)
    drainage_blockage: float | None = Field(default=None, ge=0, le=100)

    model_config = ConfigDict(extra="allow")


class RiskAssessment(BaseModel):
    risk_type: Literal["waterlogging"]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    probability: float
    location: str
    environmental_data: dict[str, Any] | None = None
    timestamp: str | None = None

    model_config = ConfigDict(extra="allow")


class EvidenceItem(BaseModel):
    source: str
    excerpt: str
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_method: str | None = None


class AIInterpretation(BaseModel):
    risk_explanation: str
    affected_areas: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    evidence: list[EvidenceItem] = Field(default_factory=list)
    source: Literal["mock", "bedrock", "fallback"] = "mock"
    model_id: str | None = None
    error: str | None = None


class IncidentApprovalRequest(BaseModel):
    approved: bool
    reviewer: str = Field(default="campus-operator")
    notes: str | None = None


class TaskStatusUpdate(BaseModel):
    status: Literal["planned", "in_progress", "completed", "blocked"]
    note: str | None = None


class ScenarioSimulationResult(BaseModel):
    simulation: bool
    persisted: bool
    external_actions: bool
    input: EnvironmentalInput
    risk_assessment: RiskAssessment
    impact_analysis: dict[str, Any]
    response_plan: dict[str, Any]


class ExecutionStageRecord(BaseModel):
    stage: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    input: dict[str, Any]
    output: Any = None
    evidence_references: list[str] = Field(default_factory=list)
    error: str | None = None


class ExecutionTraceRecord(BaseModel):
    execution_id: str
    started_at: str
    completed_at: str | None = None
    status: str
    orchestration: str
    ai_mode: str
    input: dict[str, Any]
    stages: list[ExecutionStageRecord] = Field(default_factory=list)
    incident_id: str | None = None


class MonitorResponse(BaseModel):
    demo_mode: bool
    source: str
    data_freshness: str | None = None
    latest_readings: dict[str, Any] | None = None
    recent_executions: list[ExecutionTraceRecord] = Field(default_factory=list)
    incident_count: int


class KnowledgeDocument(BaseModel):
    name: str
    type: str
    excerpt: str
    verified_document: bool
    used_by: list[dict[str, Any]] = Field(default_factory=list)
    recommendation_mapping: str


class KnowledgeResponse(BaseModel):
    demo_mode: bool
    documents: list[KnowledgeDocument] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    demo_mode: bool
    source: str
    incident_total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_day: list[dict[str, Any]]
    approvals: dict[str, int]
    tasks: dict[str, Any]
    mean_detection_to_decision_seconds: float | None = None


class IncidentRecord(BaseModel):
    incident_id: str
    location: str
    risk_type: Literal["waterlogging"]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    probability: float
    environmental_data: dict[str, Any]
    timestamp: str
    status: Literal["open", "pending_approval", "approved", "rejected", "resolved"] = "pending_approval"
    response_plan: dict[str, Any] | None = None
    ai_summary: dict[str, Any] | None = None
    approval_notes: str | None = None
    approval_reviewer: str | None = None
    approval_timestamp: str | None = None
    execution_id: str | None = None
    execution_trace: dict[str, Any] | None = None
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    audit_events: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")
