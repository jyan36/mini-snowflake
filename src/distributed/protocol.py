from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    task_id: str
    kind: str
    payload: dict[str, object]


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    kind: str
    payload: dict[str, object]


@dataclass(frozen=True)
class TaskStatus:
    task_id: str
    state: str
    message: str = ""


@dataclass(frozen=True)
class Heartbeat:
    worker_id: str
    healthy: bool = True
    message: str = ""
