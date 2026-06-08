from __future__ import annotations

from dataclasses import dataclass, field
from multiprocessing import get_context

from distributed.protocol import Task
from distributed.transport import QueueTransport
from distributed.worker import Worker
from distributed.shuffle import ShuffleExchange
from storage import from_rows


@dataclass
class ProcessWorkerHandle:
    worker_id: str
    transport: QueueTransport
    process: object

    def stop(self) -> None:
        self.transport.send_task(Task(f"stop-{self.worker_id}", "stop", {}))
        self.process.join(timeout=5)


@dataclass
class ProcessWorkerPool:
    workers: dict[str, ProcessWorkerHandle] = field(default_factory=dict)
    _context: object = field(default_factory=lambda: _best_context())

    def add_worker(self, worker_id: str, tables: dict[str, object]) -> ProcessWorkerHandle:
        task_queue = self._context.Queue()
        result_queue = self._context.Queue()
        transport = QueueTransport(task_queue, result_queue)
        process = self._context.Process(target=_worker_main, args=(worker_id, transport, tables), daemon=True)
        process.start()
        handle = ProcessWorkerHandle(worker_id, transport, process)
        self.workers[worker_id] = handle
        return handle

    def stop_all(self) -> None:
        for handle in self.workers.values():
            handle.stop()

    def distributed_join(
        self,
        left: list[dict[str, object]],
        right: list[dict[str, object]],
        left_key: str,
        right_key: str,
    ) -> list[dict[str, object]]:
        if not self.workers:
            return []
        exchange = ShuffleExchange(partitions=max(1, len(self.workers)))
        left_partitions = exchange.partition(from_rows("left", left).batch(), left_key)
        right_partitions = exchange.partition(from_rows("right", right).batch(), right_key)
        worker_ids = list(self.workers.keys())
        for index, worker_id in enumerate(worker_ids):
            handle = self.workers[worker_id]
            handle.transport.send_task(
                Task(
                    f"join-{index}",
                    "join",
                    {
                        "left_rows": left_partitions[index % len(left_partitions)].rows,
                        "right_rows": right_partitions[index % len(right_partitions)].rows,
                        "left_key": left_key,
                        "right_key": right_key,
                    },
                )
            )
        rows = []
        for worker_id in worker_ids:
            result = self._wait_for_result(worker_id)
            rows.extend(result.payload.get("rows", []))
        return sorted(rows, key=lambda row: row.get("name", tuple(row[key] for key in sorted(row.keys()))))

    def distributed_count(self, rows: list[dict[str, object]], group_key: str) -> list[dict[str, object]]:
        if not self.workers:
            return []
        exchange = ShuffleExchange(partitions=max(1, len(self.workers)))
        partitions = exchange.partition(from_rows("grouped", rows).batch(), group_key)
        worker_ids = list(self.workers.keys())
        for index, worker_id in enumerate(worker_ids):
            handle = self.workers[worker_id]
            handle.transport.send_task(
                Task(
                    f"aggregate-{index}",
                    "aggregate",
                    {
                        "rows": partitions[index % len(partitions)].rows,
                        "group_key": group_key,
                    },
                )
            )
        combined: dict[object, int] = {}
        for worker_id in worker_ids:
            result = self._wait_for_result(worker_id)
            for key, value in result.payload.get("counts", {}).items():
                combined[key] = combined.get(key, 0) + int(value)
        return [{group_key: key, "count": count} for key, count in sorted(combined.items(), key=lambda item: item[0])]

    def _wait_for_result(self, worker_id: str):
        handle = self.workers[worker_id]
        result = handle.transport.receive_result()
        while result is None:
            result = handle.transport.receive_result()
        return result


def _worker_main(worker_id: str, transport: QueueTransport, tables: dict[str, object]) -> None:
    worker = Worker(worker_id, transport, tables)
    worker.run_forever()


def _best_context():
    try:
        return get_context("fork")
    except ValueError:
        return get_context("spawn")
