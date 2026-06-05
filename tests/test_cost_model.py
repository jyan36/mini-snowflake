import unittest

from planner import CostModel, LogicalPlanner
from sql_parser import Parser


class CostModelTest(unittest.TestCase):
    def test_join_cost_is_higher_than_scan(self) -> None:
        model = CostModel()
        scan = LogicalPlanner().plan(Parser().parse("select name from people"))
        join = LogicalPlanner().plan(Parser().parse("select name from people join cities on people = cities"))

        self.assertGreater(model.estimate(join).total, model.estimate(scan).total)

    def test_filter_reduces_rows(self) -> None:
        model = CostModel()
        plan = LogicalPlanner().plan(Parser().parse("select name from people where age = 10"))
        self.assertLess(model.estimate(plan).rows, 1000.0)

