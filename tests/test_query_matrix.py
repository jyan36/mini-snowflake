import unittest

from execution import ExecutionEngine
from planner import LogicalPlanner
from session import QuerySession
from sql_parser import Parser
from storage import from_rows


class QueryMatrixTest(unittest.TestCase):
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

    def test_join_query(self) -> None:
        query = Parser().parse("select name, city_name from people join cities on city_id = id where age >= 12")
        rows = ExecutionEngine().execute(LogicalPlanner().plan(query), {"people": self.people, "cities": self.cities})
        self.assertEqual(
            rows,
            [
                {"name": "bob", "city_name": "vancouver"},
                {"name": "carol", "city_name": "seattle"},
            ],
        )

    def test_group_by_query(self) -> None:
        query = Parser().parse("select city, count(*) from people group by city order by city")
        rows = ExecutionEngine().execute(LogicalPlanner().plan(query), {"people": self.people})
        self.assertEqual(rows, [{"city": "seattle", "count": 2}, {"city": "vancouver", "count": 1}])

    def test_cte_query(self) -> None:
        query = Parser().parse(
            "with older as (select name, city from people where age >= 12) select name from older order by name"
        )
        rows = ExecutionEngine().execute(LogicalPlanner().plan(query), {"people": self.people})
        self.assertEqual(rows, [{"name": "bob"}, {"name": "carol"}])

    def test_star_query(self) -> None:
        query = Parser().parse("select * from people where age > 10 order by age")
        rows = ExecutionEngine().execute(LogicalPlanner().plan(query), {"people": self.people})
        self.assertEqual(
            rows,
            [
                {"id": 2, "name": "bob", "age": 12, "city_id": 200, "city": "vancouver"},
                {"id": 3, "name": "carol", "age": 15, "city_id": 100, "city": "seattle"},
            ],
        )

    def test_explain_shows_plan(self) -> None:
        output = QuerySession().explain("select city, count(*) from people group by city order by city")
        self.assertIn("Aggregate", output)
        self.assertIn("Sort", output)

