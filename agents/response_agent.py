from __future__ import annotations

from typing import Any


def build_response_plan(risk_assessment: dict[str, Any], impact: dict[str, Any]) -> dict[str, Any]:
    severity = risk_assessment.get("severity", "MEDIUM")
    if severity == "CRITICAL":
        actions = [
            "Close the most affected entrances",
            "Redirect pedestrian traffic to safe routes",
            "Alert maintenance and emergency teams",
        ]
    elif severity == "HIGH":
        actions = [
            "Inspect drainage points",
            "Increase staff monitoring",
            "Prepare restricted access signage",
        ]
    else:
        actions = ["Continue routine monitoring", "Review rainfall trend"]

    return {
        "recommended_actions": actions,
        "priority": severity,
        "location": impact.get("location", "Unknown"),
    }
