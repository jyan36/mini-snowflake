from __future__ import annotations

from dataclasses import dataclass

from sql_parser.ast import FunctionCall, Query


@dataclass(frozen=True, slots=True)
class LogicalPlan:
    pass


@dataclass(frozen=True, slots=True)
class Scan(LogicalPlan):
    table: str


@dataclass(frozen=True, slots=True)
class CtePlan(LogicalPlan):
    name: str
    plan: LogicalPlan


@dataclass(frozen=True, slots=True)
class Filter(LogicalPlan):
    input: LogicalPlan
    predicate: object


@dataclass(frozen=True, slots=True)
class Projection(LogicalPlan):
    input: LogicalPlan
    expressions: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class Join(LogicalPlan):
    left: LogicalPlan
    right: LogicalPlan
    condition: object
    strategy: str = "hash"


@dataclass(frozen=True, slots=True)
class Aggregate(LogicalPlan):
    input: LogicalPlan
    group_by: tuple[object, ...]
    aggregates: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class Sort(LogicalPlan):
    input: LogicalPlan
    order_by: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class With(LogicalPlan):
    ctes: tuple[tuple[str, LogicalPlan], ...]
    input: LogicalPlan


class LogicalPlanner:
    def plan(self, query: Query) -> LogicalPlan:
        plan: LogicalPlan = Scan(query.source.name)
        for join in query.joins:
            plan = Join(plan, Scan(join.table.name), join.condition)
        if query.where is not None:
            plan = Filter(plan, query.where)
        has_aggregate = query.group_by or any(isinstance(item.expression, FunctionCall) for item in query.select)
        if has_aggregate:
            plan = Aggregate(plan, query.group_by, tuple(item.expression for item in query.select))
        else:
            plan = Projection(plan, tuple(item.expression for item in query.select))
        if query.order_by:
            plan = Sort(plan, tuple(item.expression for item in query.order_by))
        if query.ctes:
            cte_plans = tuple((cte.name, self.plan(cte.query)) for cte in query.ctes)
            plan = With(cte_plans, plan)
        return plan

    def join_strategy(self, left_rows: float, right_rows: float) -> str:
        if min(left_rows, right_rows) <= 100:
            return "broadcast"
        if left_rows + right_rows > 10_000:
            return "sort_merge"
        return "hash"
