from __future__ import annotations

from dataclasses import dataclass

from sql_parser.ast import Query


@dataclass(frozen=True, slots=True)
class LogicalPlan:
    pass


@dataclass(frozen=True, slots=True)
class Scan(LogicalPlan):
    table: str


@dataclass(frozen=True, slots=True)
class Filter(LogicalPlan):
    input: LogicalPlan
    predicate: object


@dataclass(frozen=True, slots=True)
class Projection(LogicalPlan):
    input: LogicalPlan
    expressions: tuple[object, ...]


class LogicalPlanner:
    def plan(self, query: Query) -> LogicalPlan:
        plan: LogicalPlan = Scan(query.source.name)
        if query.where is not None:
            plan = Filter(plan, query.where)
        plan = Projection(plan, tuple(item.expression for item in query.select))
        return plan
