import unittest

from execution import ExecutionEngine
from execution.scheduler import LocalScheduler
from planner import LogicalPlanner
from sql_parser import Parser


class ParallelControlsTest(unittest.TestCase):
    def test_sequential_mode_is_reported(self) -> None:
        engine = ExecutionEngine()
        plan = LogicalPlanner().plan(Parser().parse("select name from people"))
        self.assertEqual(engine.execution_mode, "sequential")
        self.assertIn("mode=sequential", engine.execution_summary(plan))

    def test_parallel_mode_is_reported(self) -> None:
        engine = ExecutionEngine(scheduler=LocalScheduler(workers=2, batch_size=2))
        plan = LogicalPlanner().plan(Parser().parse("select name from people"))
        self.assertEqual(engine.execution_mode, "parallel")
        self.assertIn("mode=parallel", engine.execution_summary(plan))
        self.assertIn("workers=2", engine.execution_summary(plan))

