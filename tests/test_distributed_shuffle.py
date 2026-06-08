import unittest

from distributed import ShuffleExchange
from storage import from_rows


class DistributedShuffleTest(unittest.TestCase):
    def test_partition_and_materialize(self) -> None:
        table = from_rows(
            "people",
            [
                {"name": "alice", "city": "seattle"},
                {"name": "bob", "city": "vancouver"},
                {"name": "carol", "city": "seattle"},
            ],
        )
        exchange = ShuffleExchange(partitions=2)
        partitions = exchange.partition(table.batch(), "city")

        self.assertEqual(len(partitions), 2)
        self.assertEqual(sum(len(partition.rows) for partition in partitions), 3)
        materialized = exchange.materialize(partitions)
        self.assertEqual(materialized.row_count, 3)

