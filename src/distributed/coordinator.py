from __future__ import annotations

from dataclasses import dataclass, field

from distributed.protocol import Task, TaskResult
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
