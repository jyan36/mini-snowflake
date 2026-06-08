from __future__ import annotations

from dataclasses import dataclass

from planner import Aggregate, Filter, Join, LogicalPlan, Projection, Scan, Sort, With
from sql_parser.ast import BinaryExpression, FunctionCall, Identifier, Literal, Star
from storage import Table, from_rows


@dataclass(frozen=True)
class RowExecutor:
    def execute(self, plan: LogicalPlan, tables: dict[str, Table]) -> list[dict[str, object]]:
        return self._execute_plan(plan, tables)

    def _execute_plan(self, plan: LogicalPlan, tables: dict[str, Table]) -> list[dict[str, object]]:
        if isinstance(plan, With):
            local_tables = dict(tables)
            for name, cte_plan in plan.ctes:
                local_tables[name] = from_rows(name, self._execute_plan(cte_plan, local_tables))
            return self._execute_plan(plan.input, local_tables)
        if isinstance(plan, Scan):
            table = tables[plan.table]
            return [table.batch().row(i) for i in range(table.batch().row_count)]
        if isinstance(plan, Filter):
            return [row for row in self._execute_plan(plan.input, tables) if self._evaluate(plan.predicate, row)]
        if isinstance(plan, Projection):
            rows = self._execute_plan(plan.input, tables)
            return [self._project_row(row, plan.expressions) for row in rows]
        if isinstance(plan, Join):
            return self._join(
                self._execute_plan(plan.left, tables),
                self._execute_plan(plan.right, tables),
                plan.condition,
            )
        if isinstance(plan, Aggregate):
            return self._aggregate(
                self._execute_plan(plan.input, tables),
                plan.group_by,
                plan.aggregates,
            )
        if isinstance(plan, Sort):
            rows = self._execute_plan(plan.input, tables)
            rows.sort(key=lambda row: tuple(self._evaluate(expression, row) for expression in plan.order_by))
            return rows
        raise ValueError(f"unsupported plan {plan!r}")

    def _project_row(self, row: dict[str, object], expressions: tuple[object, ...]) -> dict[str, object]:
        projected: dict[str, object] = {}
        for expression in expressions:
            if isinstance(expression, Star):
                projected.update(row)
            elif isinstance(expression, Identifier):
                projected[expression.name] = row[expression.name]
            elif isinstance(expression, Literal):
                projected["literal"] = expression.value
            elif isinstance(expression, FunctionCall) and expression.name.lower() == "count" and expression.arguments == (Star(),):
                projected["count"] = 1
            else:
                raise ValueError(f"unsupported projection {expression!r}")
        return projected

    def _join(self, left_rows: list[dict[str, object]], right_rows: list[dict[str, object]], condition: object) -> list[dict[str, object]]:
        results = []
        for left in left_rows:
            for right in right_rows:
                combined = {**left, **right}
                if self._evaluate(condition, combined):
                    results.append(combined)
        return results

    def _aggregate(
        self,
        rows: list[dict[str, object]],
        group_by: tuple[object, ...],
        aggregates: tuple[object, ...],
    ) -> list[dict[str, object]]:
        grouped: dict[tuple[object, ...], list[dict[str, object]]] = {}
        for row in rows:
            key = tuple(self._evaluate(expression, row) for expression in group_by)
            grouped.setdefault(key, []).append(row)
        results = []
        for key, group_rows in grouped.items():
            row: dict[str, object] = {}
            for index, expression in enumerate(group_by):
                row[self._name(expression)] = key[index]
            for expression in aggregates:
                row[self._name(expression)] = self._aggregate_expression(expression, group_rows)
            results.append(row)
        return results

    def _aggregate_expression(self, expression: object, rows: list[dict[str, object]]) -> object:
        if isinstance(expression, Identifier):
            return self._evaluate(expression, rows[0])
        if isinstance(expression, FunctionCall):
            name = expression.name.lower()
            if name == "count":
                return len(rows)
            if name == "sum":
                return sum(self._evaluate(expression.arguments[0], row) for row in rows)
            if name == "min":
                return min(self._evaluate(expression.arguments[0], row) for row in rows)
            if name == "max":
                return max(self._evaluate(expression.arguments[0], row) for row in rows)
        raise ValueError(f"unsupported aggregate {expression!r}")

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
        if isinstance(expression, FunctionCall):
            return self._name(expression)
        if isinstance(expression, Star):
            return row
        raise ValueError(f"unsupported expression {expression!r}")

    def _name(self, expression: object) -> str:
        if isinstance(expression, Identifier):
            return expression.name
        if isinstance(expression, FunctionCall):
            return expression.name.lower()
        return "expr"

