from __future__ import annotations

from dataclasses import dataclass

from planner import LogicalPlanner, Optimizer
from sql_parser import Parser


@dataclass
class QuerySession:
    parser: Parser = Parser()
    planner: LogicalPlanner = LogicalPlanner()
    optimizer: Optimizer = Optimizer()

    def plan(self, sql: str):
        query = self.parser.parse(sql)
        return self.planner.plan(query)

    def optimized_plan(self, sql: str):
        return self.optimizer.optimize(self.plan(sql))

    def explain(self, sql: str) -> str:
        return repr(self.optimized_plan(sql))
