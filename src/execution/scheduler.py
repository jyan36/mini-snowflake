from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from storage import Batch, Table


class LocalScheduler:
    def __init__(self, workers: int = 1, batch_size: int = 2) -> None:
        self.workers = max(1, workers)
        self.batch_size = max(1, batch_size)

    def scan(self, table: Table) -> Batch:
        batches = table.partitioned_batches(self.batch_size)
        if self.workers == 1 or len(batches) <= 1:
            return self._merge_batches(batches)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            results = list(pool.map(lambda batch: batch, batches))
        return self._merge_batches(results)

    def _merge_batches(self, batches: list[Batch]) -> Batch:
        if not batches:
            return Batch(())
        if len(batches) == 1:
            return batches[0]
        names = tuple(column.name for column in batches[0].columns)
        columns = []
        for index, name in enumerate(names):
            values = tuple(value for batch in batches for value in batch.columns[index].values)
            columns.append(batches[0].columns[index].__class__(name, values))
        return Batch(tuple(columns))

