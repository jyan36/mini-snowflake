from __future__ import annotations

from dataclasses import dataclass

from planner import LogicalPlanner
from sql_parser import Parser


@dataclass(slots=True)
class QuerySession:
    parser: Parser = Parser()
    planner: LogicalPlanner = LogicalPlanner()

    def explain(self, sql: str) -> str:
        query = self.parser.parse(sql)
        plan = self.planner.plan(query)
        return repr(plan)
