import unittest

from catalog import StatsCatalog, TableStats
from execution import ExecutionEngine
from execution.scheduler import LocalScheduler
from planner import LogicalPlanner, Optimizer
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

    def test_join_strategy_visible_in_explain(self) -> None:
        stats = StatsCatalog()
        stats.register("people", TableStats(1000))
        stats.register("cities", TableStats(10))
        session = QuerySession(optimizer=Optimizer(stats=stats))
        output = session.explain("select name from people join cities on city_id = id")
        self.assertIn("strategy='broadcast'", output)

    def test_complex_query_matrix(self) -> None:
        people = from_rows(
            "people",
            [
                {"id": 1, "name": "alice", "age": 10, "city_id": 100, "city": "seattle"},
                {"id": 2, "name": "bob", "age": 12, "city_id": 200, "city": "vancouver"},
                {"id": 3, "name": "carol", "age": 15, "city_id": 100, "city": "seattle"},
            ],
        )
        cities = from_rows(
            "cities",
            [
                {"id": 100, "city_name": "seattle"},
                {"id": 200, "city_name": "vancouver"},
            ],
        )
        query = Parser().parse(
            "select name, city_name from people join cities on city_id = id where age >= 12 order by name"
        )
        rows = ExecutionEngine().execute(LogicalPlanner().plan(query), {"people": people, "cities": cities})
        self.assertEqual(
            rows,
            [
                {"name": "bob", "city_name": "vancouver"},
                {"name": "carol", "city_name": "seattle"},
            ],
        )

    def test_parallel_engine_matches_sequential(self) -> None:
        people = from_rows(
            "people",
            [
                {"id": 1, "name": "alice", "age": 10, "city_id": 100, "city": "seattle"},
                {"id": 2, "name": "bob", "age": 12, "city_id": 200, "city": "vancouver"},
                {"id": 3, "name": "carol", "age": 15, "city_id": 100, "city": "seattle"},
                {"id": 4, "name": "dave", "age": 18, "city_id": 200, "city": "vancouver"},
            ],
        )
        cities = from_rows(
            "cities",
            [
                {"id": 100, "city_name": "seattle"},
                {"id": 200, "city_name": "vancouver"},
            ],
        )
        query = Parser().parse(
            "select name, city_name from people join cities on city_id = id where age >= 12 order by name"
        )
        plan = LogicalPlanner().plan(query)
        sequential = ExecutionEngine().execute(plan, {"people": people, "cities": cities})
        parallel_engine = ExecutionEngine(scheduler=LocalScheduler(workers=2, batch_size=2))
        parallel = parallel_engine.execute(plan, {"people": people, "cities": cities})

        self.assertEqual(sequential, parallel)
        self.assertIn("mode=parallel", parallel_engine.execution_summary(plan))
