import unittest

from distributed import Coordinator


class WorkerHealthTest(unittest.TestCase):
    def test_worker_health_refreshed(self) -> None:
        coordinator = Coordinator()
        coordinator.register_worker("worker-a")
        health = coordinator.refresh_health()
        self.assertIn("worker-a", health)
        self.assertTrue(health["worker-a"].healthy)

    def test_healthy_workers_list(self) -> None:
        coordinator = Coordinator()
        coordinator.register_worker("worker-a")
        coordinator.refresh_health()
        self.assertEqual(coordinator.healthy_workers(), ["worker-a"])

