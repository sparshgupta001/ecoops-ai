from __future__ import annotations

import json
import os
from typing import Any


class NotificationService:
    def __init__(self):
        self.enabled = os.getenv("AWS_SNS_ENABLED", "false").lower() == "true"

    def send_incident_alert(self, incident: dict[str, Any], recommended_actions: list[str] | None = None) -> dict[str, Any]:
        message = {
            "INCIDENT": "waterlogging",
            "Location": incident.get("location", "Unknown"),
            "Risk": incident.get("severity", "HIGH"),
            "Severity": incident.get("severity", "HIGH"),
            "Recommended actions": recommended_actions or ["Inspect drainage", "Redirect pedestrians", "Alert campus teams"],
        }

        if not self.enabled:
            return {
                "mode": "mock",
                "status": "simulated",
                "message": message,
            }

        try:
            import boto3

            topic_arn = os.getenv("AWS_SNS_TOPIC_ARN")
            if not topic_arn:
                raise ValueError("AWS_SNS_TOPIC_ARN is required")
            client = boto3.client("sns", region_name=os.getenv("AWS_REGION", "us-east-1"))
            response = client.publish(
                TopicArn=topic_arn,
                Subject="EcoOps AI Incident Alert",
                Message=json.dumps(message),
            )
            return {"mode": "aws_sns", "status": "sent", "message_id": response.get("MessageId")}
        except Exception as exc:
            return {"mode": "aws_sns", "status": "failed", "error": str(exc), "message": message}


notification_service = NotificationService()
