from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from storage import Batch, Column


@dataclass(frozen=True)
class ShufflePartition:
    partition_id: int
    rows: list[dict[str, object]]


@dataclass
class ShuffleExchange:
    partitions: int = 2

    def partition(self, batch: Batch, key: str) -> list[ShufflePartition]:
        buckets = [list() for _ in range(max(1, self.partitions))]
        for index in range(batch.row_count):
            row = batch.row(index)
            buckets[hash(row[key]) % len(buckets)].append(row)
        return [ShufflePartition(index, rows) for index, rows in enumerate(buckets)]

    def materialize(self, partitions: list[ShufflePartition]) -> Batch:
        rows = [row for partition in partitions for row in partition.rows]
        if not rows:
            return Batch(())
        names = tuple(rows[0].keys())
        return Batch(tuple(Column(name, tuple(row[name] for row in rows)) for name in names))

    def checkpoint(self, partitions: list[ShufflePartition], path: str | Path) -> Path:
        checkpoint_path = Path(path)
        payload = [
            {"partition_id": partition.partition_id, "rows": partition.rows}
            for partition in partitions
        ]
        checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")
        return checkpoint_path

    def restore(self, path: str | Path) -> list[ShufflePartition]:
        checkpoint_path = Path(path)
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        return [ShufflePartition(item["partition_id"], list(item["rows"])) for item in payload]
