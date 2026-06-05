import unittest

from execution import ExecutionEngine
from planner import Aggregate, Join, LogicalPlanner, Sort, With
from sql_parser import FunctionCall, Identifier, Parser, Star
from storage import from_rows


class SqlFeatureTest(unittest.TestCase):
    def test_parse_join(self) -> None:
        query = Parser().parse("select name from people join cities on people = cities")
        self.assertEqual(query.joins[0].table.name, "cities")

    def test_parse_group_by_and_aggregate(self) -> None:
        query = Parser().parse("select count(*) from people group by city")
        self.assertEqual(query.group_by, (Identifier("city"),))
        self.assertEqual(query.select[0].expression, FunctionCall("count", (Star(),)))

    def test_parse_order_by(self) -> None:
        query = Parser().parse("select name from people order by name desc")
        self.assertEqual(query.order_by[0].expression, Identifier("name"))
        self.assertTrue(query.order_by[0].descending)

    def test_parse_cte(self) -> None:
        query = Parser().parse("with filtered as (select name from people) select name from filtered")
        self.assertEqual(query.ctes[0].name, "filtered")

    def test_planner_builds_join(self) -> None:
        query = Parser().parse("select name from people join cities on people = cities")
        plan = LogicalPlanner().plan(query)
        self.assertIsInstance(plan.input, Join)

    def test_planner_builds_aggregate(self) -> None:
        query = Parser().parse("select count(*) from people group by city")
        plan = LogicalPlanner().plan(query)
        self.assertIsInstance(plan, Aggregate)

    def test_planner_builds_sort(self) -> None:
        query = Parser().parse("select name from people order by name desc")
        plan = LogicalPlanner().plan(query)
        self.assertIsInstance(plan, Sort)

    def test_engine_executes_cte(self) -> None:
        people = from_rows(
            "people",
            [
                {"name": "alice", "age": 10},
                {"name": "bob", "age": 12},
            ],
        )
        plan = LogicalPlanner().plan(
            Parser().parse("with filtered as (select name from people where age = 12) select name from filtered")
        )
        rows = ExecutionEngine().execute(plan, {"people": people})
        self.assertEqual(rows, [{"name": "bob"}])
