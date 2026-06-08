import unittest

from benchmark import BenchmarkCase, benchmark_case, build_cities_table, build_people_table


class BenchmarkTest(unittest.TestCase):
    def test_benchmark_case_returns_timings(self) -> None:
        result = benchmark_case(
            BenchmarkCase("join", "select name, city_name from people join cities on city_id = id order by name"),
            build_people_table(20),
            build_cities_table(),
        )
        self.assertIn("sequential_ms", result)
        self.assertIn("parallel_ms", result)
        self.assertIn("distributed_ms", result)

