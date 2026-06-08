import unittest

from distributed import Coordinator


class FailureValidationTest(unittest.TestCase):
    def test_failed_worker_is_marked_unhealthy(self) -> None:
        coordinator = Coordinator()
        worker = coordinator.register_worker("worker-a")
        coordinator.refresh_health()

        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        worker.execute = boom  # type: ignore[method-assign]
        with self.assertRaises(RuntimeError):
            coordinator.execute_with_retry("custom", {"value": 1}, retries=0)

        self.assertFalse(coordinator.worker_health["worker-a"].healthy)

    def test_distributed_count_validation_after_retry(self) -> None:
        coordinator = Coordinator()
        worker_a = coordinator.register_worker("worker-a")
        worker_b = coordinator.register_worker("worker-b")
        coordinator.refresh_health()

        rows = [
            {"city": "seattle"},
            {"city": "vancouver"},
            {"city": "seattle"},
        ]
        result = coordinator.distributed_count(rows, "city")
        self.assertEqual(result, [{"city": "seattle", "count": 2}, {"city": "vancouver", "count": 1}])

