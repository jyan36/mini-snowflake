import unittest

from execution import ExecutionEngine
from planner import LogicalPlanner
from session import QuerySession
from sql_parser import Parser
from storage import from_rows


class IntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.table = from_rows(
            "people",
            [
                {"name": "alice", "age": 10, "city": "seattle"},
                {"name": "bob", "age": 12, "city": "vancouver"},
                {"name": "carol", "age": 15, "city": "seattle"},
            ],
        )
        self.tables = {"people": self.table}

    def test_select_filter_projection(self) -> None:
        query = Parser().parse("select name, city from people where age >= 12 and city = 'vancouver'")
        plan = LogicalPlanner().plan(query)
        rows = ExecutionEngine().execute(plan, self.tables)
        self.assertEqual(rows, [{"name": "bob", "city": "vancouver"}])

    def test_select_star(self) -> None:
        query = Parser().parse("select * from people where city = 'seattle'")
        plan = LogicalPlanner().plan(query)
        rows = ExecutionEngine().execute(plan, self.tables)
        self.assertEqual(
            rows,
            [
                {"name": "alice", "age": 10, "city": "seattle"},
                {"name": "carol", "age": 15, "city": "seattle"},
            ],
        )

    def test_session_explain_is_structured(self) -> None:
        output = QuerySession().explain("select name from people where age >= 12")
        self.assertIn("Projection", output)
        self.assertIn("Filter", output)
        self.assertIn("Scan", output)

