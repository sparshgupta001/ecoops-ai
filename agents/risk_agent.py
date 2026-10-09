from __future__ import annotations

from typing import Any

from backend.services.ai_service import ai_service
from backend.services.risk_service import calculate_risk


class RiskAgent:
    def __init__(self):
        self.ai_service = ai_service

    def assess(self, event: dict[str, Any]) -> dict[str, Any]:
        risk = calculate_risk(event)
        explanation = self.ai_service.generate_response(
            environmental_data=event,
            risk_assessment=risk,
            context=["Campus drainage map", "Flood response guidance"],
        )
        return {
            "risk": risk,
            "explanation": explanation,
        }


risk_agent = RiskAgent()
