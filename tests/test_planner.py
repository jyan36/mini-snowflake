import unittest

from planner import Filter, LogicalPlanner, Projection, Scan
from sql_parser import Identifier, Literal, Parser


class LogicalPlannerTest(unittest.TestCase):
    def test_plan_select_where(self) -> None:
        query = Parser().parse("select name from people where age = 10")
        plan = LogicalPlanner().plan(query)

        self.assertIsInstance(plan, Projection)
        self.assertEqual(plan.expressions, (Identifier("name"),))
        self.assertIsInstance(plan.input, Filter)
        self.assertIsInstance(plan.input.input, Scan)
        self.assertEqual(plan.input.input.table, "people")
        self.assertEqual(
            plan.input.predicate,
            query.where,
        )

    def test_plan_without_where(self) -> None:
        query = Parser().parse("select name from people")
        plan = LogicalPlanner().plan(query)

        self.assertIsInstance(plan, Projection)
        self.assertIsInstance(plan.input, Scan)
        self.assertEqual(plan.expressions, (Identifier("name"),))

    def test_plan_with_join(self) -> None:
        query = Parser().parse("select name from people join cities on people = cities")
        plan = LogicalPlanner().plan(query)
        self.assertEqual(plan.input.__class__.__name__, "Join")

    def test_plan_with_group_by(self) -> None:
        query = Parser().parse("select city, count(*) from people group by city")
        plan = LogicalPlanner().plan(query)
        self.assertEqual(plan.__class__.__name__, "Aggregate")
