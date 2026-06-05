import unittest

from catalog import StatsCatalog, TableStats
from planner import LogicalPlanner, Optimizer
from sql_parser import Parser


class JoinStrategyTest(unittest.TestCase):
    def test_small_side_uses_broadcast(self) -> None:
        plan = LogicalPlanner().plan(Parser().parse("select name from people join cities on people = cities"))
        stats = StatsCatalog()
        stats.register("people", TableStats(1000))
        stats.register("cities", TableStats(10))
        optimized = Optimizer(stats=stats).optimize(plan)
        self.assertEqual(optimized.input.strategy, "broadcast")

    def test_join_strategy_is_recorded(self) -> None:
        plan = LogicalPlanner().plan(Parser().parse("select name from people join cities on people = cities"))
        stats = StatsCatalog()
        stats.register("people", TableStats(1000))
        stats.register("cities", TableStats(10))
        optimized = Optimizer(stats=stats).optimize(plan)
        self.assertIn(optimized.input.strategy, {"broadcast", "hash", "sort_merge"})
