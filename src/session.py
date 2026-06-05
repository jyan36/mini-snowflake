from __future__ import annotations

from dataclasses import dataclass

from planner import LogicalPlanner, Optimizer
from sql_parser import Parser


@dataclass(slots=True)
class QuerySession:
    parser: Parser = Parser()
    planner: LogicalPlanner = LogicalPlanner()
    optimizer: Optimizer = Optimizer()

    def explain(self, sql: str) -> str:
        query = self.parser.parse(sql)
        plan = self.optimizer.optimize(self.planner.plan(query))
        return repr(plan)
