import unittest

from execution import ExecutionEngine
from planner import LogicalPlanner
from sql_parser import Parser
from storage import from_rows


class ParallelScanTest(unittest.TestCase):
    def test_parallel_scan_matches_sequential(self) -> None:
        table = from_rows(
            "people",
            [
                {"name": "alice", "age": 10},
                {"name": "bob", "age": 12},
                {"name": "carol", "age": 15},
                {"name": "dave", "age": 18},
            ],
        )
        sequential = [table.batch().row(i) for i in range(table.batch().row_count)]
        parallel = ExecutionEngine().scheduler.__class__(workers=2).scan(table)

        self.assertEqual(sequential, [parallel.row(i) for i in range(parallel.row_count)])

    def test_partitioned_batches_split_data(self) -> None:
        table = from_rows(
            "people",
            [
                {"name": "alice", "age": 10},
                {"name": "bob", "age": 12},
                {"name": "carol", "age": 15},
            ],
        )
        batches = table.partitioned_batches(2)
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0].row_count, 2)
        self.assertEqual(batches[1].row_count, 1)
