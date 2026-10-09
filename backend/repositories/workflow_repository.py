from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR


class WorkflowRepository:
    def __init__(self, storage_path: str | Path | None = None):
        self.storage_path = Path(storage_path) if storage_path else BASE_DIR / "data" / "executions.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def list_executions(self) -> list[dict[str, Any]]:
        try:
            records = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return records if isinstance(records, list) else []

    def get_execution(self, execution_id: str) -> dict[str, Any] | None:
        return next(
            (item for item in self.list_executions() if item.get("execution_id") == execution_id),
            None,
        )

    def save_execution(self, execution: dict[str, Any]) -> dict[str, Any]:
        records = self.list_executions()
        for index, current in enumerate(records):
            if current.get("execution_id") == execution.get("execution_id"):
                records[index] = execution
                break
        else:
            records.append(execution)
        self.storage_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return execution


workflow_repository = WorkflowRepository()