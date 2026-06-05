import unittest

from execution import ExecutionEngine, FilterOperator, ProjectionOperator, ScanOperator
from planner import LogicalPlanner
from sql_parser import Parser
from storage import from_rows


class ExecutionTest(unittest.TestCase):
    def test_filter_and_projection(self) -> None:
        table = from_rows(
            "people",
            [
                {"name": "alice", "age": 10},
                {"name": "bob", "age": 12},
            ],
        )
        plan = LogicalPlanner().plan(Parser().parse("select name from people where age = 12"))
        rows = ExecutionEngine().execute(plan, {"people": table})

        self.assertEqual(rows, [{"name": "bob"}])

