from __future__ import annotations

from dataclasses import dataclass, field
from queue import Empty
from typing import Any

from distributed.protocol import Task, TaskResult


@dataclass
class LocalTransport:
    inbox: list[Task] = field(default_factory=list)
    outbox: list[TaskResult] = field(default_factory=list)

    def send_task(self, task: Task | None) -> None:
        if task is None:
            return
        self.inbox.append(task)

    def receive_task(self, block: bool = False, timeout: float | None = None) -> Task | None:
        if not self.inbox:
            return None
        return self.inbox.pop(0)

    def send_result(self, result: TaskResult) -> None:
        self.outbox.append(result)

    def receive_result(self) -> TaskResult | None:
        if not self.outbox:
            return None
        return self.outbox.pop(0)


@dataclass
class QueueTransport:
    task_queue: Any
    result_queue: Any

    def send_task(self, task: Task | None) -> None:
        self.task_queue.put(task)

    def receive_task(self, block: bool = False, timeout: float | None = None) -> Task | None:
        try:
            if block:
                return self.task_queue.get(timeout=timeout)
            return self.task_queue.get_nowait()
        except Empty:
            return None

    def send_result(self, result: TaskResult) -> None:
        self.result_queue.put(result)

    def receive_result(self) -> TaskResult | None:
        try:
            return self.result_queue.get_nowait()
        except Empty:
            return None
