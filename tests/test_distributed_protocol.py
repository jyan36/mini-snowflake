import unittest

from distributed import Coordinator, LocalTransport, Task, TaskResult, Worker
from storage import from_rows


class DistributedProtocolTest(unittest.TestCase):
    def test_task_round_trip(self) -> None:
        transport = LocalTransport()
        coordinator = Coordinator(transport=transport)
        worker = coordinator.register_worker("worker-1")
        worker.tables["people"] = from_rows("people", [{"name": "alice"}])

        coordinator.submit("scan", {"table": "people"})
        result = worker.execute()
        self.assertIsNotNone(result)
        self.assertEqual(result.kind, "completed")
        self.assertEqual(result.payload["worker_id"], "worker-1")
        self.assertEqual(coordinator.collect(), [result])

    def test_worker_poll_returns_none_when_idle(self) -> None:
        transport = LocalTransport()
        worker = Worker("worker-1", transport)
        self.assertIsNone(worker.poll())
