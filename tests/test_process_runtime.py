import unittest

from distributed import ProcessWorkerPool
from storage import from_rows


class ProcessRuntimeTest(unittest.TestCase):
    def test_execute_query_filters_rows(self) -> None:
        pool = ProcessWorkerPool()
        pool.add_worker(
            "worker-a",
            {
                "people": from_rows(
                    "people",
                    [
                        {"name": "alice", "age": 10, "city_id": 100, "city": "seattle", "score": 1, "segment": "s1"},
                        {"name": "bob", "age": 12, "city_id": 200, "city": "vancouver", "score": 2, "segment": "s2"},
                    ],
                ),
                "cities": from_rows("cities", [{"id": 100, "city_name": "seattle"}, {"id": 200, "city_name": "vancouver"}]),
            },
        )
        pool.add_worker(
            "worker-b",
            {
                "people": from_rows(
                    "people",
                    [
                        {"name": "carl", "age": 14, "city_id": 100, "city": "seattle", "score": 3, "segment": "s3"},
                        {"name": "dana", "age": 9, "city_id": 200, "city": "vancouver", "score": 4, "segment": "s4"},
                    ],
                ),
                "cities": from_rows("cities", [{"id": 100, "city_name": "seattle"}, {"id": 200, "city_name": "vancouver"}]),
            },
        )
        rows = pool.execute_query("select name from people where age >= 10", {})
        self.assertEqual(rows, [{"name": "alice"}, {"name": "bob"}, {"name": "carl"}])
        pool.stop_all()

    def test_execute_query_joins_rows(self) -> None:
        pool = ProcessWorkerPool()
        pool.add_worker(
            "worker-a",
            {
                "people": from_rows(
                    "people",
                    [
                        {"name": "alice", "age": 10, "city_id": 100, "city": "seattle", "score": 1, "segment": "s1"},
                        {"name": "bob", "age": 12, "city_id": 200, "city": "vancouver", "score": 2, "segment": "s2"},
                    ],
                ),
                "cities": from_rows("cities", [{"id": 100, "city_name": "seattle"}, {"id": 200, "city_name": "vancouver"}]),
            },
        )
        pool.add_worker(
            "worker-b",
            {
                "people": from_rows(
                    "people",
                    [
                        {"name": "carl", "age": 14, "city_id": 100, "city": "seattle", "score": 3, "segment": "s3"},
                        {"name": "dana", "age": 9, "city_id": 200, "city": "vancouver", "score": 4, "segment": "s4"},
                    ],
                ),
                "cities": from_rows("cities", [{"id": 100, "city_name": "seattle"}, {"id": 200, "city_name": "vancouver"}]),
            },
        )
        rows = pool.execute_query("select name, city_name from people join cities on city_id = id order by name", {})
        self.assertEqual(
            rows,
            [
                {"name": "alice", "city_name": "seattle"},
                {"name": "bob", "city_name": "vancouver"},
                {"name": "carl", "city_name": "seattle"},
                {"name": "dana", "city_name": "vancouver"},
            ],
        )
        pool.stop_all()
