import unittest

from planner import Filter, LogicalPlanner, Optimizer, Projection
from sql_parser import BinaryExpression, Identifier, Literal, Parser


class OptimizerTest(unittest.TestCase):
    def test_constant_folding(self) -> None:
        query = Parser().parse("select name from people where 1 = 1 and 2 = 2")
        plan = Optimizer().optimize(LogicalPlanner().plan(query))
        self.assertIsInstance(plan.input, Filter)
        self.assertEqual(plan.input.predicate, Literal(True))

    def test_projection_passthrough(self) -> None:
        query = Parser().parse("select name from people")
        plan = Optimizer().optimize(LogicalPlanner().plan(query))
        self.assertIsInstance(plan, Projection)
        self.assertEqual(plan.expressions, (Identifier("name"),))

