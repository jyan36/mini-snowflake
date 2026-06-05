from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class QuerySession:
    def explain(self, sql: str) -> str:
        normalized = " ".join(sql.split())
        return f"unparsed query: {normalized}"

