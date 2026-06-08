from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColumnStats:
    distinct_count: int | None = None
    null_count: int | None = None
    min_value: object | None = None
    max_value: object | None = None


@dataclass(frozen=True)
class TableStats:
    row_count: int
    columns: dict[str, ColumnStats] = field(default_factory=dict)


@dataclass
class StatsCatalog:
    tables: dict[str, TableStats] = field(default_factory=dict)

    def register(self, name: str, stats: TableStats) -> None:
        self.tables[name] = stats

    def get(self, name: str) -> TableStats | None:
        return self.tables.get(name)
