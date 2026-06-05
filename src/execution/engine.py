from __future__ import annotations

from dataclasses import dataclass

from execution.operators import AggregateOperator, FilterOperator, JoinOperator, ProjectionOperator, ScanOperator, SortOperator
from execution.scheduler import LocalScheduler
from planner import Aggregate, Filter, Join, LogicalPlan, Optimizer, Projection, Scan, Sort, With
from storage import Table


@dataclass(frozen=True, slots=True)
class ExecutionEngine:
    optimizer: Optimizer = Optimizer()
    scheduler: LocalScheduler = LocalScheduler()

    def execute(self, plan: LogicalPlan, tables: dict[str, Table]) -> list[dict[str, object]]:
        batch = self._execute_batch(self.optimizer.optimize(plan), tables)
        return [batch.row(index) for index in range(batch.row_count)]

    def _execute_batch(self, plan: LogicalPlan, tables: dict[str, Table]):
        if isinstance(plan, With):
            local_tables = dict(tables)
            for name, cte_plan in plan.ctes:
                local_rows = self.execute(cte_plan, local_tables)
                local_tables[name] = self._rows_to_table(name, local_rows)
            return self._execute_batch(plan.input, local_tables)
        if isinstance(plan, Projection):
            batch = self._execute_batch(plan.input, tables)
            return ProjectionOperator(plan.expressions).execute(batch)
        if isinstance(plan, Sort):
            batch = self._execute_batch(plan.input, tables)
            return SortOperator(plan.order_by).execute(batch)
        if isinstance(plan, Aggregate):
            batch = self._execute_batch(plan.input, tables)
            if self.scheduler.workers > 1:
                return self.scheduler.aggregate(batch, plan.group_by, plan.aggregates)
            return AggregateOperator(plan.group_by, plan.aggregates).execute(batch)
        if isinstance(plan, Filter):
            batch = self._execute_batch(plan.input, tables)
            return FilterOperator(plan.predicate).execute(batch)
        if isinstance(plan, Join):
            left = self._execute_batch(plan.left, tables)
            right = self._execute_batch(plan.right, tables)
            return self.scheduler.join(left, right, plan.condition)
        if isinstance(plan, Scan):
            if self.scheduler.workers > 1:
                return self.scheduler.scan(tables[plan.table])
            return ScanOperator(tables[plan.table]).execute()
        raise ValueError(f"unsupported plan {plan!r}")

    def _rows_to_table(self, name: str, rows: list[dict[str, object]]) -> Table:
        if not rows:
            return Table(name, ())
        from storage import from_rows

        return from_rows(name, rows)
