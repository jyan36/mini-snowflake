import unittest
from pathlib import Path
import tempfile

from benchmark import BenchmarkCase, _render_report, benchmark_case, build_cities_table, build_people_table


class BenchmarkReportTest(unittest.TestCase):
    def test_render_report_contains_cases(self) -> None:
        people = build_people_table(20)
        cities = build_cities_table()
        result = benchmark_case(
            BenchmarkCase("join", "select name, city_name from people join cities on city_id = id order by name"),
            people,
            cities,
        )
        report = _render_report([result])
        self.assertIn("# Benchmark Report", report)
        self.assertIn("join", report)
        self.assertIn("Row", report)
        self.assertIn("Speedup", report)
