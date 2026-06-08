from __future__ import annotations

from dataclasses import dataclass, field

from distributed.protocol import Task, TaskResult


@dataclass
class LocalTransport:
    inbox: list[Task] = field(default_factory=list)
    outbox: list[TaskResult] = field(default_factory=list)

    def send_task(self, task: Task) -> None:
        self.inbox.append(task)

    def receive_task(self) -> Task | None:
        if not self.inbox:
            return None
        return self.inbox.pop(0)

    def send_result(self, result: TaskResult) -> None:
        self.outbox.append(result)

    def receive_result(self) -> TaskResult | None:
        if not self.outbox:
            return None
        return self.outbox.pop(0)

