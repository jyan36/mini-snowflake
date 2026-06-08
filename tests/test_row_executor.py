import unittest

from execution import ExecutionEngine, RowExecutor
from planner import LogicalPlanner
from sql_parser import Parser
from storage import from_rows


class RowExecutorTest(unittest.TestCase):
    def test_row_and_vectorized_match(self) -> None:
        table = from_rows(
            "people",
            [
                {"name": "alice", "age": 10, "city": "seattle"},
                {"name": "bob", "age": 12, "city": "vancouver"},
                {"name": "carol", "age": 15, "city": "seattle"},
            ],
        )
        query = Parser().parse("select name, city from people where age >= 12 order by name")
        plan = LogicalPlanner().plan(query)
        vectorized = ExecutionEngine().execute(plan, {"people": table})
        row_based = RowExecutor().execute(plan, {"people": table})
        self.assertEqual(vectorized, row_based)

