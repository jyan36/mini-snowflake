import unittest

from distributed import Coordinator


class DistributedRetryTest(unittest.TestCase):
    def test_retry_uses_healthy_worker(self) -> None:
        coordinator = Coordinator()
        worker_a = coordinator.register_worker("worker-a")
        worker_b = coordinator.register_worker("worker-b")
        worker_a.tables["people"] = None
        worker_b.tables["people"] = None
        coordinator.refresh_health()

        result = coordinator.execute_with_retry("custom", {"value": 1}, retries=1)
        self.assertEqual(result.kind, "completed")
        self.assertIn(result.payload["worker_id"], {"worker-a", "worker-b"})

