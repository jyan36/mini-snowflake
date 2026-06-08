from __future__ import annotations

from dataclasses import dataclass, field

from distributed.protocol import Task, TaskResult
from distributed.shuffle import ShuffleExchange
from distributed.transport import LocalTransport
from distributed.worker import Worker


@dataclass
class Coordinator:
    transport: LocalTransport = field(default_factory=LocalTransport)
    workers: dict[str, Worker] = field(default_factory=dict)

    def register_worker(self, worker_id: str) -> Worker:
        worker = Worker(worker_id, self.transport, {})
        self.workers[worker_id] = worker
        return worker

    def submit(self, kind: str, payload: dict[str, object]) -> Task:
        task = Task(f"{kind}-{len(self.transport.inbox) + len(self.transport.outbox)}", kind, payload)
        self.transport.send_task(task)
        return task

    def submit_scan(self, table: str) -> Task:
        return self.submit("scan", {"table": table})

    def distributed_join(self, left: list[dict[str, object]], right: list[dict[str, object]], left_key: str, right_key: str) -> list[dict[str, object]]:
        if not self.workers:
            return self._join_locally(left, right, left_key, right_key)
        exchange = ShuffleExchange(partitions=max(1, len(self.workers)))
        left_partitions = exchange.partition(self._rows_to_batch(left), left_key)
        right_partitions = exchange.partition(self._rows_to_batch(right), right_key)
        worker_ids = list(self.workers.keys())
        for index, worker_id in enumerate(worker_ids):
            left_rows = left_partitions[index % len(left_partitions)].rows
            right_rows = right_partitions[index % len(right_partitions)].rows
            self.submit(
                "join",
                {"left_rows": left_rows, "right_rows": right_rows, "left_key": left_key, "right_key": right_key},
            )
            self.workers[worker_id].execute()
        results = self.collect()
        rows = [row for result in results for row in result.payload.get("rows", [])]
        return sorted(rows, key=lambda row: row.get("name", tuple(row[key] for key in sorted(row.keys()))))

    def distributed_count(self, rows: list[dict[str, object]], group_key: str) -> list[dict[str, object]]:
        if not self.workers:
            return self._count_locally(rows, group_key)
        exchange = ShuffleExchange(partitions=max(1, len(self.workers)))
        partitions = exchange.partition(self._rows_to_batch(rows), group_key)
        worker_ids = list(self.workers.keys())
        for index, worker_id in enumerate(worker_ids):
            partition_rows = partitions[index % len(partitions)].rows
            self.submit("aggregate", {"rows": partition_rows, "group_key": group_key})
            self.workers[worker_id].execute()
        results = self.collect()
        combined: dict[object, int] = {}
        for result in results:
            for key, value in result.payload.get("counts", {}).items():
                combined[key] = combined.get(key, 0) + int(value)
        return [{group_key: key, "count": count} for key, count in sorted(combined.items(), key=lambda item: item[0])]

    def collect(self) -> list[TaskResult]:
        results = []
        while True:
            result = self.transport.receive_result()
            if result is None:
                break
            results.append(result)
        return results

    def run_once(self) -> list[TaskResult]:
        for worker in self.workers.values():
            worker.execute()
        return self.collect()

    def _rows_to_batch(self, rows: list[dict[str, object]]):
        from storage import from_rows

        return from_rows("distributed", rows).batch()

    def _join_locally(
        self,
        left: list[dict[str, object]],
        right: list[dict[str, object]],
        left_key: str,
        right_key: str,
    ) -> list[dict[str, object]]:
        rows = []
        hash_table: dict[object, list[dict[str, object]]] = {}
        for row in left:
            hash_table.setdefault(row[left_key], []).append(row)
        for row in right:
            for left_row in hash_table.get(row[right_key], []):
                rows.append({**left_row, **row})
        return rows

    def _count_locally(self, rows: list[dict[str, object]], group_key: str) -> list[dict[str, object]]:
        counts: dict[object, int] = {}
        for row in rows:
            counts[row[group_key]] = counts.get(row[group_key], 0) + 1
        return [{group_key: key, "count": count} for key, count in sorted(counts.items(), key=lambda item: item[0])]
