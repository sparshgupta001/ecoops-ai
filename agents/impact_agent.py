from __future__ import annotations

from typing import Any


def assess_impact(risk_assessment: dict[str, Any], environmental_data: dict[str, Any]) -> dict[str, Any]:
    severity = risk_assessment.get("severity", "MEDIUM")
    if severity in {"HIGH", "CRITICAL"}:
        impacts = ["Student movement", "Parking zones", "Utility corridors", "Low-lying access roads"]
    else:
        impacts = ["Minor foot traffic delays", "Surface runoff watchlist"]

    return {"impact": impacts, "severity": severity, "location": environmental_data.get("location", "Unknown")}
