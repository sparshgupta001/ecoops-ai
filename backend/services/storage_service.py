from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR


class LocalObjectStore:
    def __init__(self, root_dir: str | None = None):
        self.root_dir = Path(root_dir) if root_dir else BASE_DIR / "data"
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, key: str, payload: dict[str, Any]) -> str:
        path = self.root_dir / f"{key}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    def read_json(self, key: str) -> dict[str, Any]:
        path = self.root_dir / f"{key}.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def list_json(self) -> list[str]:
        return sorted(str(item.name) for item in self.root_dir.glob("*.json"))


object_store = LocalObjectStore()
