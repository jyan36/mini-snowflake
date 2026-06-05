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

