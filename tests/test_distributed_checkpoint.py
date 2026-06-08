import tempfile
import unittest
from pathlib import Path

from distributed import ShuffleExchange
from storage import from_rows


class DistributedCheckpointTest(unittest.TestCase):
    def test_shuffle_checkpoint_round_trip(self) -> None:
        table = from_rows(
            "people",
            [
                {"name": "alice", "city": "seattle"},
                {"name": "bob", "city": "vancouver"},
            ],
        )
        exchange = ShuffleExchange(partitions=2)
        partitions = exchange.partition(table.batch(), "city")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "shuffle.json"
            saved = exchange.checkpoint(partitions, path)
            restored = exchange.restore(saved)

        self.assertEqual([partition.rows for partition in restored], [partition.rows for partition in partitions])

