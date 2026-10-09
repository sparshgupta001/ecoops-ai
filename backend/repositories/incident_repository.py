from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR, settings


class LocalIncidentRepository:
    def __init__(self, storage_path: str | None = None):
        self.storage_path = Path(storage_path) if storage_path else BASE_DIR / "data" / "incidents.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def list_incidents(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = []
        if not isinstance(data, list):
            return []

        seen_ids: set[str] = set()
        changed = False
        for incident in data:
            incident_id = incident.get("incident_id")
            if not incident_id or incident_id in seen_ids:
                incident_id = f"INC-{uuid.uuid4().hex[:10].upper()}"
                incident["incident_id"] = incident_id
                changed = True
            seen_ids.add(incident_id)

        if changed:
            self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def create_incident(self, incident: dict[str, Any]) -> dict[str, Any]:
        incidents = self.list_incidents()
        incident_id = incident.get("incident_id") or uuid.uuid4().hex[:8]
        incident["incident_id"] = incident_id
        incidents.append(incident)
        self.storage_path.write_text(json.dumps(incidents, indent=2), encoding="utf-8")
        return incident

    def upsert_incident(self, incident: dict[str, Any]) -> dict[str, Any]:
        incidents = self.list_incidents()
        incident_id = incident.get("incident_id") or uuid.uuid4().hex[:8]
        incident["incident_id"] = incident_id
        for index, current in enumerate(incidents):
            if current.get("incident_id") == incident_id:
                incidents[index] = incident
                break
        else:
            incidents.append(incident)
        self.storage_path.write_text(json.dumps(incidents, indent=2), encoding="utf-8")
        return incident

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        for incident in self.list_incidents():
            if incident.get("incident_id") == incident_id:
                return incident
        return None

    def update_incident(self, incident_id: str, incident: dict[str, Any]) -> dict[str, Any]:
        incidents = self.list_incidents()
        for index, current in enumerate(incidents):
            if current.get("incident_id") == incident_id:
                incidents[index] = incident
                self.storage_path.write_text(json.dumps(incidents, indent=2), encoding="utf-8")
                return incident
        raise KeyError(f"Incident {incident_id} not found")

    def clear(self) -> None:
        self.storage_path.write_text("[]", encoding="utf-8")


class DynamoDBIncidentRepository:
    def __init__(self, table_name: str | None = None):
        self.table_name = table_name or settings.AWS_DYNAMODB_TABLE
        self.client = None
        try:
            import boto3

            self.client = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
        except Exception:
            self.client = None

    def list_incidents(self) -> list[dict[str, Any]]:
        if self.client is None:
            return []
        try:
            table = self.client.Table(self.table_name)
            response = table.scan()
            return response.get("Items", [])
        except Exception:
            return []

    def create_incident(self, incident: dict[str, Any]) -> dict[str, Any] | None:
        if self.client is None:
            return None
        try:
            table = self.client.Table(self.table_name)
            incident_id = incident.get("incident_id") or uuid.uuid4().hex[:8]
            incident["incident_id"] = incident_id
            table.put_item(Item=incident)
            return incident
        except Exception:
            return None

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        if self.client is None:
            return None
        try:
            table = self.client.Table(self.table_name)
            response = table.get_item(Key={"incident_id": incident_id})
            return response.get("Item")
        except Exception:
            return None

    def update_incident(self, incident_id: str, incident: dict[str, Any]) -> dict[str, Any] | None:
        if self.client is None:
            return None
        try:
            table = self.client.Table(self.table_name)
            table.put_item(Item={**incident, "incident_id": incident_id})
            return incident
        except Exception:
            return None


class IncidentRepository:
    def __init__(self):
        self._local = LocalIncidentRepository()
        self._dynamodb = DynamoDBIncidentRepository() if settings.AWS_DYNAMODB_ENABLED else None

    def list_incidents(self) -> list[dict[str, Any]]:
        if self._dynamodb is not None:
            items = self._dynamodb.list_incidents()
            if items:
                return items
        return self._local.list_incidents()

    def create_incident(self, incident: dict[str, Any]) -> dict[str, Any]:
        if self._dynamodb is not None:
            item = self._dynamodb.create_incident(incident)
            if item is not None:
                self._local.upsert_incident(item)
                return item
        return self._local.create_incident(incident)

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        if self._dynamodb is not None:
            item = self._dynamodb.get_incident(incident_id)
            if item is not None:
                return item
        return self._local.get_incident(incident_id)

    def update_incident(self, incident_id: str, incident: dict[str, Any]) -> dict[str, Any]:
        if self._dynamodb is not None:
            item = self._dynamodb.update_incident(incident_id, incident)
            if item is not None:
                self._local.upsert_incident(item)
                return item
        return self._local.update_incident(incident_id, incident)


incident_repository = IncidentRepository()
