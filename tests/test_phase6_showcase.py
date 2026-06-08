import os
import tempfile
import unittest
from pathlib import Path

from benchmark import main as benchmark_main
from examples.workload import build_demo_workload


class Phase6ShowcaseTest(unittest.TestCase):
    def test_benchmark_writes_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                benchmark_main([])
                self.assertTrue(Path("benchmark_results.csv").exists())
                self.assertTrue(Path("benchmark_report.md").exists())
                report = Path("benchmark_report.md").read_text(encoding="utf-8")
                self.assertIn("# Benchmark Report", report)
            finally:
                os.chdir(cwd)

    def test_demo_workload_has_cases(self) -> None:
        cases = build_demo_workload()
        self.assertGreaterEqual(len(cases), 3)

