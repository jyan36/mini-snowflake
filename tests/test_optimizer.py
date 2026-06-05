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

    def test_join_strategy_defaults(self) -> None:
        query = Parser().parse("select name from people join cities on people = cities")
        plan = Optimizer().optimize(LogicalPlanner().plan(query))
        self.assertIn(plan.input.strategy, {"broadcast", "hash", "sort_merge"})

    def test_order_by_is_preserved(self) -> None:
        query = Parser().parse("select name from people order by name desc")
        plan = Optimizer().optimize(LogicalPlanner().plan(query))
        self.assertEqual(plan.__class__.__name__, "Sort")

    def test_with_clause_is_preserved(self) -> None:
        query = Parser().parse("with filtered as (select name from people) select name from filtered")
        plan = Optimizer().optimize(LogicalPlanner().plan(query))
        self.assertEqual(plan.__class__.__name__, "With")
