from __future__ import annotations

from dataclasses import dataclass

from distributed.protocol import Task, TaskResult
from distributed.transport import LocalTransport


@dataclass
class Worker:
    worker_id: str
    transport: LocalTransport

    def poll(self) -> Task | None:
        return self.transport.receive_task()

    def execute(self) -> TaskResult | None:
        task = self.poll()
        if task is None:
            return None
        result = TaskResult(task.task_id, "completed", {"worker_id": self.worker_id, **task.payload})
        self.transport.send_result(result)
        return result

