import unittest

from planner import Filter, LogicalPlanner, Optimizer, Projection
from sql_parser import Identifier, Parser


class RewriteTest(unittest.TestCase):
    def test_projection_pushdown_preserves_filter(self) -> None:
        query = Parser().parse("select name from people where age = 10")
        plan = Optimizer().optimize(LogicalPlanner().plan(query))
        self.assertIsInstance(plan, Projection)
        self.assertIsInstance(plan.input, Filter)

    def test_projection_pruning_keeps_simple_projection(self) -> None:
        query = Parser().parse("select name from people")
        plan = Optimizer().optimize(LogicalPlanner().plan(query))
        self.assertIsInstance(plan, Projection)
        self.assertEqual(plan.expressions, (Identifier("name"),))

