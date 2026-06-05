from __future__ import annotations

from dataclasses import dataclass

from sql_parser.ast import BinaryExpression, Identifier, Literal
from storage import Batch, Column, Table


@dataclass(frozen=True, slots=True)
class ScanOperator:
    table: Table

    def execute(self) -> Batch:
        return self.table.batch()


@dataclass(frozen=True, slots=True)
class FilterOperator:
    predicate: object

    def execute(self, batch: Batch) -> Batch:
        mask = [self._evaluate(self.predicate, batch, index) for index in range(batch.row_count)]
        columns = tuple(
            column.__class__(column.name, tuple(value for value, keep in zip(column.values, mask) if keep))
            for column in batch.columns
        )
        return Batch(columns)

    def _evaluate(self, expression: object, batch: Batch, index: int) -> object:
        if isinstance(expression, Identifier):
            return batch.column(expression.name).values[index]
        if isinstance(expression, Literal):
            return expression.value
        if isinstance(expression, BinaryExpression):
            left = self._evaluate(expression.left, batch, index)
            right = self._evaluate(expression.right, batch, index)
            if expression.operator == "=":
                return left == right
            if expression.operator == "<":
                return left < right
            if expression.operator == ">":
                return left > right
        raise ValueError(f"unsupported expression {expression!r}")


@dataclass(frozen=True, slots=True)
class ProjectionOperator:
    expressions: tuple[object, ...]

    def execute(self, batch: Batch) -> Batch:
        columns = []
        for expression in self.expressions:
            if isinstance(expression, Identifier):
                source = batch.column(expression.name)
                columns.append(source.__class__(expression.name, source.values))
                continue
            if isinstance(expression, Literal):
                columns.append(Column("literal", tuple(expression.value for _ in range(batch.row_count))))
                continue
            raise ValueError(f"unsupported projection {expression!r}")
        return Batch(tuple(columns))


def scan_rows(table: Table) -> list[dict[str, object]]:
    return [table.batch().row(index) for index in range(table.batch().row_count)]
