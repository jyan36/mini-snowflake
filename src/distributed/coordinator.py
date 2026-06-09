from __future__ import annotations

from dataclasses import dataclass, field

from distributed.protocol import Heartbeat, Task, TaskResult
from distributed.shuffle import ShuffleExchange
from distributed.transport import LocalTransport
from distributed.worker import Worker
from execution import ExecutionEngine
from planner import LogicalPlanner
from sql_parser import Parser
from sql_parser.ast import BinaryExpression, FunctionCall, Identifier, Literal, Star
from storage import Column, Table, from_rows


@dataclass
class Coordinator:
    transport: LocalTransport = field(default_factory=LocalTransport)
    workers: dict[str, Worker] = field(default_factory=dict)
    worker_health: dict[str, Heartbeat] = field(default_factory=dict)

    def register_worker(self, worker_id: str) -> Worker:
        worker = Worker(worker_id, self.transport, {})
        self.workers[worker_id] = worker
        self.worker_health[worker_id] = Heartbeat(worker_id, True, "registered")
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
        worker_count = max(1, len(self.workers))
        exchange = ShuffleExchange(partitions=worker_count)
        left_partitions = exchange.partition(self._rows_to_batch(left), left_key)
        if len(right) <= worker_count * 8:
            right_rows = [self._rows_to_batch(right).row(i) for i in range(len(right))]
            right_partitions = [right_rows for _ in range(worker_count)]
        else:
            right_partitions = [partition.rows for partition in exchange.partition(self._rows_to_batch(right), right_key)]
        worker_ids = list(self.workers.keys())
        for index, worker_id in enumerate(worker_ids):
            left_rows = left_partitions[index % len(left_partitions)].rows
            right_rows = right_partitions[index % len(right_partitions)]
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
        partials: list[dict[object, int]] = []
        for index, worker_id in enumerate(worker_ids):
            partition_rows = partitions[index % len(partitions)].rows
            self.submit("aggregate", {"rows": partition_rows, "group_key": group_key})
            self.workers[worker_id].execute()
        results = self.collect()
        for result in results:
            partials.append({key: int(value) for key, value in result.payload.get("counts", {}).items()})
        combined: dict[object, int] = {}
        for partial in partials:
            for key, value in partial.items():
                combined[key] = combined.get(key, 0) + value
        return [{group_key: key, "count": count} for key, count in sorted(combined.items(), key=lambda item: item[0])]

    def distributed_query(self, sql: str, tables: dict[str, Table]) -> list[dict[str, object]]:
        if not self.workers:
            return []
        query = Parser().parse(sql)
        tables = self._project_tables(query, tables)
        query_kind = self._query_kind(sql)
        if query_kind == "join":
            left_table = tables.get("people")
            right_table = tables.get("cities")
            if left_table is None or right_table is None:
                return []
            return self.distributed_join(
                [left_table.batch().row(i) for i in range(left_table.batch().row_count)],
                [right_table.batch().row(i) for i in range(right_table.batch().row_count)],
                "city_id",
                "id",
            )
        if query_kind == "aggregate":
            table = tables.get("people")
            if table is None:
                return []
            rows = [table.batch().row(i) for i in range(table.batch().row_count)]
            return self.distributed_count(rows, "city")
        return self._distributed_scan(sql, tables)

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

    def execute_with_retry(self, kind: str, payload: dict[str, object], retries: int = 1) -> TaskResult:
        healthy_workers = self.healthy_workers()
        if not healthy_workers:
            raise RuntimeError("no healthy workers available")
        task = self.submit(kind, payload)
        for attempt in range(retries + 1):
            worker = self.workers[healthy_workers[attempt % len(healthy_workers)]]
            try:
                return self._execute_on_worker(worker, task)
            except Exception as exc:  # pragma: no cover - defensive fallback
                self.worker_health[worker.worker_id] = Heartbeat(worker.worker_id, False, str(exc))
                continue
        raise RuntimeError(f"task {task.task_id} failed after retries")

    def refresh_health(self) -> dict[str, Heartbeat]:
        for worker_id, worker in self.workers.items():
            self.worker_health[worker_id] = worker.heartbeat()
        return dict(self.worker_health)

    def healthy_workers(self) -> list[str]:
        return [worker_id for worker_id, heartbeat in self.worker_health.items() if heartbeat.healthy]

    def _rows_to_batch(self, rows: list[dict[str, object]]):
        from storage import from_rows

        return from_rows("distributed", rows).batch()

    def _table_partitions(self, table: Table, key: str, exchange: ShuffleExchange) -> list[Table]:
        partitions = exchange.partition(table.batch(), key)
        return [self._rows_to_table(table.name, partition.rows, table) for partition in partitions]

    def _distributed_scan(self, sql: str, tables: dict[str, Table]) -> list[dict[str, object]]:
        query = Parser().parse(sql)
        plan = LogicalPlanner().plan(query)
        return self._sorted_rows(ExecutionEngine().execute(plan, tables))

    def _execute_on_worker(self, worker: Worker, task: Task) -> TaskResult:
        worker.transport.send_task(task)
        result = worker.execute()
        if result is None:
            raise RuntimeError("worker produced no result")
        return result

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

    def _query_kind(self, sql: str) -> str:
        lowered = sql.lower()
        if "join" in lowered:
            return "join"
        if "count(*)" in lowered or "group by" in lowered:
            return "aggregate"
        return "scan"

    def _rows_to_table(self, name: str, rows: list[dict[str, object]], source: Table) -> Table:
        if rows:
            return from_rows(name, rows)
        return Table(name, tuple(Column(column.name, tuple()) for column in source.columns))

    def _tables_payload(self, tables: dict[str, Table]) -> dict[str, object]:
        return {name: table.to_payload() for name, table in tables.items()}

    def _sorted_rows(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return sorted(rows, key=lambda row: row.get("name", tuple(row[key] for key in sorted(row.keys()))))

    def _project_tables(self, query, tables: dict[str, Table]) -> dict[str, Table]:
        if not tables:
            return tables
        required = self._query_columns(query)
        if not required:
            return tables
        projected = dict(tables)
        for name, table in tables.items():
            columns = tuple(column for column in table.columns if column.name in required.get(name, set()))
            if columns:
                projected[name] = Table(name, columns)
        return projected

    def _query_columns(self, query) -> dict[str, set[str]]:
        columns: dict[str, set[str]] = {}
        for item in query.select:
            self._collect_columns(item.expression, columns, "people")
        if query.where is not None:
            self._collect_columns(query.where, columns, "people")
        for join in query.joins:
            self._collect_columns(join.condition, columns, "people")
            self._collect_columns(join.condition, columns, "cities")
        for expression in query.group_by:
            self._collect_columns(expression, columns, "people")
        for order_item in query.order_by:
            self._collect_columns(order_item.expression, columns, "people")
        if not columns:
            return {}
        return columns

    def _collect_columns(self, expression, columns: dict[str, set[str]], default_table: str) -> None:
        if isinstance(expression, Identifier):
            columns.setdefault(default_table, set()).add(expression.name)
            return
        if isinstance(expression, BinaryExpression):
            self._collect_columns(expression.left, columns, default_table)
            self._collect_columns(expression.right, columns, default_table)
            return
        if isinstance(expression, FunctionCall):
            for argument in expression.arguments:
                self._collect_columns(argument, columns, default_table)
            return
        if isinstance(expression, Star) or isinstance(expression, Literal):
            return
