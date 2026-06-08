import unittest

from benchmark import BenchmarkCase, benchmark_case, build_cities_table, build_people_table


class BenchmarkTest(unittest.TestCase):
    def test_benchmark_case_returns_timings(self) -> None:
        result = benchmark_case(
            BenchmarkCase("join", "select name, city_name from people join cities on city_id = id order by name"),
            build_people_table(200),
            build_cities_table(),
        )
        self.assertIn("sequential_ms", result)
        self.assertIn("parallel_ms", result)
        self.assertIn("distributed_ms", result)
        self.assertIn("row_speedup", result)
        self.assertGreater(result["row_rows"], 0)

    def test_parse_args_supports_output_dir_and_sizes(self) -> None:
        from benchmark import _parse_args

        args = _parse_args(["--people-size", "1234", "--warmup-runs", "3", "--sample-runs", "9", "--output-dir", "tmp-bench"])
        self.assertEqual(args.people_size, 1234)
        self.assertEqual(args.warmup_runs, 3)
        self.assertEqual(args.sample_runs, 9)
        self.assertEqual(args.output_dir, "tmp-bench")
