import unittest

from distributed import Coordinator


class DistributedQueriesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.coordinator = Coordinator()
        worker_a = self.coordinator.register_worker("worker-a")
        worker_b = self.coordinator.register_worker("worker-b")
        self.workers = (worker_a, worker_b)

    def test_distributed_join_matches_expected_rows(self) -> None:
        left = [
            {"id": 1, "name": "alice", "city_id": 100},
            {"id": 2, "name": "bob", "city_id": 200},
            {"id": 3, "name": "carol", "city_id": 100},
        ]
        right = [
            {"id": 100, "city_name": "seattle"},
            {"id": 200, "city_name": "vancouver"},
        ]

        rows = self.coordinator.distributed_join(left, right, "city_id", "id")
        self.assertEqual(
            rows,
            [
                {"id": 100, "name": "alice", "city_id": 100, "city_name": "seattle"},
                {"id": 200, "name": "bob", "city_id": 200, "city_name": "vancouver"},
                {"id": 100, "name": "carol", "city_id": 100, "city_name": "seattle"},
            ],
        )

    def test_distributed_count_matches_expected_rows(self) -> None:
        rows = [
            {"city": "seattle"},
            {"city": "vancouver"},
            {"city": "seattle"},
        ]

        result = self.coordinator.distributed_count(rows, "city")
        self.assertEqual(result, [{"city": "seattle", "count": 2}, {"city": "vancouver", "count": 1}])

