import unittest

from execution import ExecutionEngine
from execution.scheduler import LocalScheduler
from planner import LogicalPlanner
from sql_parser import Parser
from storage import from_rows


class ParallelAggregateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.people = from_rows(
            "people",
            [
                {"name": "alice", "age": 10, "city": "seattle"},
                {"name": "bob", "age": 12, "city": "vancouver"},
                {"name": "carol", "age": 15, "city": "seattle"},
                {"name": "dave", "age": 18, "city": "vancouver"},
            ],
        )

    def test_parallel_aggregate_matches_sequential(self) -> None:
        query = Parser().parse("select city, count(*) from people group by city order by city")
        plan = LogicalPlanner().plan(query)
        sequential = ExecutionEngine().execute(plan, {"people": self.people})
        parallel = ExecutionEngine(scheduler=LocalScheduler(workers=2, batch_size=2)).execute(
            plan, {"people": self.people}
        )
        self.assertEqual(sequential, parallel)

