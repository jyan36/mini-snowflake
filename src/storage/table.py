from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Column:
    name: str
    values: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class Batch:
    columns: tuple[Column, ...]

    @property
    def row_count(self) -> int:
        return len(self.columns[0].values) if self.columns else 0

    def column(self, name: str) -> Column:
        for column in self.columns:
            if column.name == name:
                return column
        raise KeyError(name)

    def row(self, index: int) -> dict[str, object]:
        return {column.name: column.values[index] for column in self.columns}


@dataclass(frozen=True, slots=True)
class Table:
    name: str
    columns: tuple[Column, ...]

    def batch(self) -> Batch:
        return Batch(self.columns)


def from_rows(name: str, rows: list[dict[str, object]]) -> Table:
    if not rows:
        return Table(name, ())
    column_names = tuple(rows[0].keys())
    columns = tuple(
        Column(column_name, tuple(row[column_name] for row in rows))
        for column_name in column_names
    )
    return Table(name, columns)

