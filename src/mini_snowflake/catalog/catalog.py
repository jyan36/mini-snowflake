from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TableDefinition:
    name: str
    columns: tuple[str, ...] = ()


@dataclass(slots=True)
class Catalog:
    tables: dict[str, TableDefinition] = field(default_factory=dict)

    def register_table(self, table: TableDefinition) -> None:
        self.tables[table.name] = table

