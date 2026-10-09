from __future__ import annotations

import json
import os
from typing import Any

from backend.models import AIInterpretation, EvidenceItem


class AIService:
    def __init__(self):
        self.enabled = os.getenv("AWS_AI_ENABLED", "false").lower() == "true"
        self.model_id = os.getenv("AWS_BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-2024-03-07-v1:0")
        self.region = os.getenv("AWS_REGION", "us-east-1")

    def generate_response(
        self,
        environmental_data: dict[str, Any],
        risk_assessment: dict[str, Any],
        context: list[str] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        evidence_list = evidence or []
        if not self.enabled:
            response = self._mock_response(environmental_data, risk_assessment, context or [], evidence_list)
            return response.model_dump()

        try:
            import boto3

            if not self.model_id:
                raise ValueError("AWS_BEDROCK_MODEL_ID is not configured")

            client = boto3.client("bedrock-runtime", region_name=self.region)
            context_text = "\n".join(context or ["campus drainage guidance"])
            evidence_text = self._build_evidence_text(evidence_list)

            prompt = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 400,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "You are a campus environmental response assistant. "
                                    "Use the provided environmental data and retrieved guidance as evidence. "
                                    "Distinguish documented facts from assumptions. "
                                    "Do not invent campus rules. If evidence is missing, say so. "
                                    "Return only valid JSON with the keys: risk_explanation, affected_areas, recommended_actions, priority, evidence, source. "
                                    f"Environmental data: {environmental_data}. "
                                    f"Risk assessment: {risk_assessment}. "
                                    f"Retrieved guidance: {context_text}. "
                                    f"Evidence documents: {evidence_text}. "
                                    "The risk_explanation must describe why the risk is high or critical using deterministic risk math and evidence. "
                                    "affected_areas should be a list of campus zones. "
                                    "recommended_actions should be clear actions for staff. "
                                    "priority must be one of LOW, MEDIUM, HIGH, CRITICAL. "
                                    "evidence should include source filenames and relevant excerpts."
                                ),
                            }
                        ],
                    }
                ],
            }

            response = client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(prompt),
                accept="application/json",
                contentType="application/json",
            )
            raw = response["body"].read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            payload = json.loads(raw)
            text = payload["content"][0]["text"]
            candidate = json.loads(text)
            candidate.setdefault("source", "bedrock")
            candidate.setdefault("model_id", self.model_id)
            candidate["evidence"] = evidence_list
            result = AIInterpretation.model_validate(candidate)
            return result.model_dump()
        except Exception as exc:  # pragma: no cover - exercised in fallback tests via environment configuration
            fallback = self._mock_response(environmental_data, risk_assessment, context or [], evidence_list)
            fallback.source = "fallback"
            fallback.error = str(exc)
            return fallback.model_dump()

    @staticmethod
    def _build_evidence_text(evidence: list[dict[str, Any]]) -> str:
        if not evidence:
            return "No retrieval evidence was found. State that the recommendation is based on deterministic calculations and available campus guidance only."
        entries = []
        for item in evidence:
            source = item.get("source", "unknown")
            excerpt = item.get("excerpt", "")
            entries.append(f"{source}: {excerpt}")
        return " | ".join(entries)

    @staticmethod
    def _mock_response(
        environmental_data: dict[str, Any],
        risk_assessment: dict[str, Any],
        context: list[str],
        evidence: list[dict[str, Any]],
    ) -> AIInterpretation:
        location = environmental_data.get("location", "campus area")
        severity = risk_assessment.get("severity", "HIGH")
        if severity == "CRITICAL":
            risk_explanation = f"Critical waterlogging risk at {location}, based on the deterministic assessment of supplied environmental inputs."
            priority = "CRITICAL"
        elif severity == "HIGH":
            risk_explanation = f"High waterlogging risk at {location}, based on the deterministic assessment of supplied environmental inputs."
            priority = "HIGH"
        else:
            risk_explanation = f"{severity.title()} waterlogging risk at {location}, based on the deterministic assessment of supplied environmental inputs."
            priority = "MEDIUM"

        evidence_items = []
        for item in evidence:
            evidence_items.append(
                EvidenceItem(
                    source=item.get("source", "local-guidance"),
                    excerpt=item.get("excerpt", "No evidence excerpt available."),
                    relevance=float(item.get("relevance", 0.5)),
                    relevance_method=item.get("relevance_method"),
                )
            )

        return AIInterpretation(
            risk_explanation=risk_explanation,
            affected_areas=[location],
            recommended_actions=[
                f"Close access points near {location}",
                "Redirect pedestrian traffic to safe routes",
                "Inspect storm drains and runoff channels",
                "Notify facilities and emergency response teams",
            ],
            priority=priority,
            evidence=evidence_items,
            source="mock",
            model_id=None,
        )


ai_service = AIService()
