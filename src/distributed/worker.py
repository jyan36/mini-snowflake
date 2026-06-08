from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from distributed.protocol import Task, TaskResult
from distributed.transport import LocalTransport
from storage import Table


@dataclass
class Worker:
    worker_id: str
    transport: LocalTransport
    tables: dict[str, Table] | None = None

    def poll(self) -> Task | None:
        return self.transport.receive_task()

    def execute(self) -> TaskResult | None:
        task = self.poll()
        if task is None:
            return None
        result = TaskResult(task.task_id, "completed", {"worker_id": self.worker_id, **self._execute_task(task)})
        self.transport.send_result(result)
        return result

    def _execute_task(self, task: Task) -> dict[str, Any]:
        if task.kind == "scan":
            table_name = str(task.payload["table"])
            table = self._require_table(table_name)
            return {"table": table_name, "rows": [table.batch().row(i) for i in range(table.batch().row_count)]}
        return dict(task.payload)

    def _require_table(self, table_name: str) -> Table:
        if self.tables is None or table_name not in self.tables:
            raise KeyError(table_name)
        return self.tables[table_name]
