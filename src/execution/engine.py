from __future__ import annotations

from dataclasses import dataclass

from execution.operators import FilterOperator, ProjectionOperator, ScanOperator
from planner import Filter, LogicalPlan, Projection, Scan
from storage import Table


@dataclass(frozen=True, slots=True)
class ExecutionEngine:
    def execute(self, plan: LogicalPlan, tables: dict[str, Table]) -> list[dict[str, object]]:
        batch = self._execute_batch(plan, tables)
        return [batch.row(index) for index in range(batch.row_count)]

    def _execute_batch(self, plan: LogicalPlan, tables: dict[str, Table]):
        if isinstance(plan, Projection):
            batch = self._execute_batch(plan.input, tables)
            return ProjectionOperator(plan.expressions).execute(batch)
        if isinstance(plan, Filter):
            batch = self._execute_batch(plan.input, tables)
            return FilterOperator(plan.predicate).execute(batch)
        if isinstance(plan, Scan):
            return ScanOperator(tables[plan.table]).execute()
        raise ValueError(f"unsupported plan {plan!r}")

