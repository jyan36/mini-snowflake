import unittest

from examples.workload import build_demo_workload


class WorkloadExamplesTest(unittest.TestCase):
    def test_demo_workload_contains_core_cases(self) -> None:
        cases = build_demo_workload()
        names = [case.name for case in cases]
        self.assertIn("join", names)
        self.assertIn("aggregate", names)
        self.assertIn("filter_projection", names)

