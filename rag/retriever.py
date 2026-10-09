from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR


class LocalRetriever:
    def __init__(self, docs_dir: str | Path | None = None):
        self.docs_dir = Path(docs_dir) if docs_dir else BASE_DIR / "rag" / "documents"

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if not query:
            return []

        normalized_query = re.findall(r"[a-z0-9]+", query.lower())
        if not normalized_query:
            return []

        results: list[dict[str, Any]] = []
        for path in sorted(self.docs_dir.glob("*.txt")):
            text = path.read_text(encoding="utf-8")
            text_lower = text.lower()
            score = 0
            for keyword in normalized_query:
                if keyword in text_lower:
                    score += 1

            if score == 0:
                continue

            excerpt = self._extract_excerpt(text, normalized_query)
            results.append(
                {
                    "source": path.name,
                    "excerpt": excerpt,
                    "relevance": round(min(score / max(len(normalized_query), 1), 1.0), 2),
                    "relevance_method": "token_overlap_heuristic",
                }
            )

        results.sort(key=lambda item: item["relevance"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _extract_excerpt(text: str, query_terms: list[str]) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            lower_line = line.lower()
            if any(term in lower_line for term in query_terms):
                return line
        return text.strip()[:220]


retriever = LocalRetriever()
