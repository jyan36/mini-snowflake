import unittest

from execution import ExecutionEngine
from execution.scheduler import LocalScheduler
from planner import LogicalPlanner
from sql_parser import Parser
from storage import from_rows


class ParallelJoinTest(unittest.TestCase):
    def setUp(self) -> None:
        self.people = from_rows(
            "people",
            [
                {"id": 1, "name": "alice", "city_id": 100},
                {"id": 2, "name": "bob", "city_id": 200},
                {"id": 3, "name": "carol", "city_id": 100},
                {"id": 4, "name": "dave", "city_id": 300},
            ],
        )
        self.cities = from_rows(
            "cities",
            [
                {"id": 100, "city_name": "seattle"},
                {"id": 200, "city_name": "vancouver"},
                {"id": 300, "city_name": "portland"},
            ],
        )

    def test_parallel_join_matches_sequential(self) -> None:
        query = Parser().parse("select name, city_name from people join cities on city_id = id order by name")
        plan = LogicalPlanner().plan(query)
        sequential = ExecutionEngine().execute(plan, {"people": self.people, "cities": self.cities})
        parallel = ExecutionEngine(scheduler=LocalScheduler(workers=2, batch_size=2)).execute(
            plan, {"people": self.people, "cities": self.cities}
        )

        self.assertEqual(sequential, parallel)

