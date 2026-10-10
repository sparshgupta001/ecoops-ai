from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR


class SensorRepository:
    def __init__(self, storage_path: str | Path | None = None):
        self.storage_path = Path(storage_path) if storage_path else BASE_DIR / "data" / "sensor_observations.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def list_observations(self) -> list[dict[str, Any]]:
        try:
            records = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(records, list):
            return []
        # Return sorted by ingested_at descending (latest first)
        return sorted(records, key=lambda item: item.get("ingested_at", item.get("timestamp", "")), reverse=True)

    def get_latest(self) -> dict[str, Any] | None:
        records = self.list_observations()
        return records[0] if records else None

    def save_observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        records = self.list_observations()
        records.insert(0, observation)
        # Keep latest 100 observations locally
        records = records[:100]
        self.storage_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return observation

    def clear(self) -> None:
        self.storage_path.write_text("[]", encoding="utf-8")


sensor_repository = SensorRepository()
