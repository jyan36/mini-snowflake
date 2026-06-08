from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from distributed.protocol import Heartbeat, Task, TaskResult
from distributed.transport import LocalTransport
from storage import Table


@dataclass
class Worker:
    worker_id: str
    transport: LocalTransport
    tables: dict[str, Table] | None = None

    def poll(self) -> Task | None:
        return self.transport.receive_task()

    def heartbeat(self) -> Heartbeat:
        return Heartbeat(self.worker_id, True, "alive")

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
        if task.kind == "join":
            left_rows = list(task.payload["left_rows"])
            right_rows = list(task.payload["right_rows"])
            left_key = str(task.payload["left_key"])
            right_key = str(task.payload["right_key"])
            rows = []
            hash_table: dict[object, list[dict[str, object]]] = {}
            for row in left_rows:
                hash_table.setdefault(row[left_key], []).append(row)
            for row in right_rows:
                for left_row in hash_table.get(row[right_key], []):
                    rows.append({**left_row, **row})
            return {"rows": rows}
        if task.kind == "aggregate":
            rows = list(task.payload["rows"])
            group_key = str(task.payload["group_key"])
            counts: dict[object, int] = {}
            for row in rows:
                counts[row[group_key]] = counts.get(row[group_key], 0) + 1
            return {"counts": counts}
        return dict(task.payload)

    def _require_table(self, table_name: str) -> Table:
        if self.tables is None or table_name not in self.tables:
            raise KeyError(table_name)
        return self.tables[table_name]
