import unittest

from catalog import StatsCatalog, TableStats
from execution import ExecutionEngine
from planner import LogicalPlanner, Optimizer
from session import QuerySession
from sql_parser import Parser
from storage import from_rows


class Phase2IntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.people = from_rows(
            "people",
            [
                {"id": 1, "name": "alice", "age": 10, "city_id": 100, "city": "seattle"},
                {"id": 2, "name": "bob", "age": 12, "city_id": 200, "city": "vancouver"},
                {"id": 3, "name": "carol", "age": 15, "city_id": 100, "city": "seattle"},
            ],
        )
        self.cities = from_rows(
            "cities",
            [
                {"id": 100, "city_name": "seattle"},
                {"id": 200, "city_name": "vancouver"},
            ],
        )

    def test_join_strategy_visible_in_explain(self) -> None:
        stats = StatsCatalog()
        stats.register("people", TableStats(1000))
        stats.register("cities", TableStats(10))
        session = QuerySession(optimizer=Optimizer(stats=stats))
        output = session.explain("select name from people join cities on city_id = id")
        self.assertIn("strategy='broadcast'", output)

    def test_complex_query_matrix(self) -> None:
        query = Parser().parse(
            "select name, city_name from people join cities on city_id = id where age >= 12 order by name"
        )
        rows = ExecutionEngine().execute(LogicalPlanner().plan(query), {"people": self.people, "cities": self.cities})
        self.assertEqual(
            rows,
            [
                {"name": "bob", "city_name": "vancouver"},
                {"name": "carol", "city_name": "seattle"},
            ],
        )

