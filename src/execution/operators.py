from __future__ import annotations

from dataclasses import dataclass

from sql_parser.ast import BinaryExpression, FunctionCall, Identifier, Literal, Star
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
            if expression.operator == "!=":
                return left != right
            if expression.operator == "<":
                return left < right
            if expression.operator == ">":
                return left > right
            if expression.operator == "<=":
                return left <= right
            if expression.operator == ">=":
                return left >= right
            if expression.operator == "AND":
                return bool(left) and bool(right)
            if expression.operator == "OR":
                return bool(left) or bool(right)
        raise ValueError(f"unsupported expression {expression!r}")


@dataclass(frozen=True, slots=True)
class ProjectionOperator:
    expressions: tuple[object, ...]

    def execute(self, batch: Batch) -> Batch:
        columns = []
        for expression in self.expressions:
            if isinstance(expression, Star):
                columns.extend(
                    Column(column.name, column.values)
                    for column in batch.columns
                )
                continue
            if isinstance(expression, Identifier):
                source = batch.column(expression.name)
                columns.append(Column(expression.name, source.values))
                continue
            if isinstance(expression, Literal):
                columns.append(Column("literal", tuple(expression.value for _ in range(batch.row_count))))
                continue
            if isinstance(expression, FunctionCall):
                if expression.name.lower() == "count" and expression.arguments == (Star(),):
                    columns.append(Column("count", (batch.row_count,)))
                    continue
            raise ValueError(f"unsupported projection {expression!r}")
        return Batch(tuple(columns))


@dataclass(frozen=True, slots=True)
class JoinOperator:
    condition: object

    def execute(self, left: Batch, right: Batch) -> Batch:
        rows = []
        for left_index in range(left.row_count):
            for right_index in range(right.row_count):
                combined = {**left.row(left_index), **right.row(right_index)}
                if self._evaluate(self.condition, combined):
                    rows.append(combined)
        if not rows:
            return Batch(())
        names = tuple(rows[0].keys())
        columns = tuple(Column(name, tuple(row[name] for row in rows)) for name in names)
        return Batch(columns)

    def _evaluate(self, expression: object, row: dict[str, object]) -> object:
        if isinstance(expression, Identifier):
            return row[expression.name]
        if isinstance(expression, Literal):
            return expression.value
        if isinstance(expression, BinaryExpression):
            left = self._evaluate(expression.left, row)
            right = self._evaluate(expression.right, row)
            if expression.operator == "=":
                return left == right
            if expression.operator == "!=":
                return left != right
            if expression.operator == "<":
                return left < right
            if expression.operator == ">":
                return left > right
            if expression.operator == "<=":
                return left <= right
            if expression.operator == ">=":
                return left >= right
            if expression.operator == "AND":
                return bool(left) and bool(right)
            if expression.operator == "OR":
                return bool(left) or bool(right)
        raise ValueError(f"unsupported join expression {expression!r}")


@dataclass(frozen=True, slots=True)
class AggregateOperator:
    group_by: tuple[object, ...]
    aggregates: tuple[object, ...]

    def execute(self, batch: Batch) -> Batch:
        groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
        for index in range(batch.row_count):
            row = batch.row(index)
            key = tuple(self._evaluate(expression, row) for expression in self.group_by)
            groups.setdefault(key, []).append(row)
        rows = []
        for key, grouped_rows in groups.items():
            row = {}
            for index, expression in enumerate(self.group_by):
                row[self._name(expression)] = key[index]
            for expression in self.aggregates:
                row[self._name(expression)] = self._aggregate(expression, grouped_rows)
            rows.append(row)
        if not rows:
            return Batch(())
        names = tuple(rows[0].keys())
        columns = tuple(Column(name, tuple(row[name] for row in rows)) for name in names)
        return Batch(columns)

    def _aggregate(self, expression: object, rows: list[dict[str, object]]) -> object:
        if isinstance(expression, FunctionCall):
            name = expression.name.lower()
            if name == "count":
                if expression.arguments == (Star(),):
                    return len(rows)
                return sum(1 for _ in rows)
            if name == "sum":
                return sum(self._evaluate(expression.arguments[0], row) for row in rows)
            if name == "max":
                return max(self._evaluate(expression.arguments[0], row) for row in rows)
            if name == "min":
                return min(self._evaluate(expression.arguments[0], row) for row in rows)
        raise ValueError(f"unsupported aggregate {expression!r}")

    def _evaluate(self, expression: object, row: dict[str, object]) -> object:
        if isinstance(expression, Identifier):
            return row[expression.name]
        if isinstance(expression, Literal):
            return expression.value
        raise ValueError(f"unsupported group expression {expression!r}")

    def _name(self, expression: object) -> str:
        if isinstance(expression, Identifier):
            return expression.name
        if isinstance(expression, FunctionCall):
            return expression.name.lower()
        return "expr"


@dataclass(frozen=True, slots=True)
class SortOperator:
    order_by: tuple[object, ...]

    def execute(self, batch: Batch) -> Batch:
        rows = [batch.row(index) for index in range(batch.row_count)]
        rows.sort(key=lambda row: tuple(self._evaluate(item, row) for item in self.order_by))
        if not rows:
            return Batch(())
        names = tuple(rows[0].keys())
        columns = tuple(Column(name, tuple(row[name] for row in rows)) for name in names)
        return Batch(columns)

    def _evaluate(self, expression: object, row: dict[str, object]) -> object:
        if isinstance(expression, Identifier):
            return row[expression.name]
        if isinstance(expression, Literal):
            return expression.value
        return row[str(expression)]


def scan_rows(table: Table) -> list[dict[str, object]]:
    return [table.batch().row(index) for index in range(table.batch().row_count)]
