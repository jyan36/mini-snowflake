import unittest

from distributed import Coordinator
from storage import from_rows


class DistributedExecutionTest(unittest.TestCase):
    def test_scan_task_returns_rows(self) -> None:
        table = from_rows(
            "people",
            [
                {"name": "alice", "age": 10},
                {"name": "bob", "age": 12},
            ],
        )
        coordinator = Coordinator()
        worker = coordinator.register_worker("worker-1")
        worker.tables["people"] = table

        coordinator.submit_scan("people")
        result = worker.execute()

        self.assertIsNotNone(result)
        self.assertEqual(result.payload["table"], "people")
        self.assertEqual(result.payload["rows"], [{"name": "alice", "age": 10}, {"name": "bob", "age": 12}])
        self.assertEqual(coordinator.collect()[0].payload["worker_id"], "worker-1")

