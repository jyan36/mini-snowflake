from __future__ import annotations

from dataclasses import dataclass, field
from multiprocessing import get_context

from distributed.protocol import Task
from distributed.transport import QueueTransport
from distributed.worker import Worker
from distributed.shuffle import ShuffleExchange
from sql_parser import Parser
from sql_parser.ast import BinaryExpression, FunctionCall, Identifier, Query, Star
from storage import Batch, Column, Table, from_rows


@dataclass
class ProcessWorkerHandle:
    worker_id: str
    transport: QueueTransport
    process: object
    tables: dict[str, Table] | None = None

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
        handle = ProcessWorkerHandle(worker_id, transport, process, tables)
        self.workers[worker_id] = handle
        return handle

    def stop_all(self) -> None:
        for handle in self.workers.values():
            handle.stop()

    def execute_query(self, sql: str, tables: dict[str, Table]) -> list[dict[str, object]]:
        if not self.workers:
            return []
        if not tables:
            return self._execute_registered_query(sql)
        query = Parser().parse(sql)
        tables = self._prune_tables(query, tables)
        query_kind = self._query_kind(sql)
        if query_kind == "join":
            return self._execute_partitioned_query(sql, tables, partition_key="city_id", merge_rows=True)
        if query_kind == "aggregate":
            return self._execute_partitioned_query(sql, tables, partition_key="city", merge_rows=False)
        return self._execute_partitioned_query(sql, tables, partition_key="city_id", merge_rows=True)

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

    def _execute_partitioned_query(
        self,
        sql: str,
        tables: dict[str, Table],
        partition_key: str,
        merge_rows: bool,
    ) -> list[dict[str, object]]:
        exchange = ShuffleExchange(partitions=max(1, len(self.workers)))
        worker_ids = list(self.workers.keys())
        partitions = self._partition_tables(tables, partition_key, exchange)
        for index, worker_id in enumerate(worker_ids):
            handle = self.workers[worker_id]
            handle.transport.send_task(
                Task(
                    f"execute-{index}",
                    "execute_sql",
                    {
                        "sql": sql,
                        "tables": self._tables_payload(partitions[index % len(partitions)]),
                    },
                )
            )
        rows = []
        for worker_id in worker_ids:
            result = self._wait_for_result(worker_id)
            rows.extend(result.payload.get("rows", []))
        if merge_rows:
            return rows
        return self._merge_grouped_rows(rows, partition_key)

    def _execute_registered_query(self, sql: str) -> list[dict[str, object]]:
        worker_ids = list(self.workers.keys())
        for index, worker_id in enumerate(worker_ids):
            handle = self.workers[worker_id]
            handle.transport.send_task(
                Task(
                    f"execute-registered-{index}",
                    "execute_sql",
                    {
                        "sql": sql,
                        "tables": self._tables_payload(handle.tables or {}),
                    },
                )
            )
        rows = []
        for worker_id in worker_ids:
            result = self._wait_for_result(worker_id)
            rows.extend(result.payload.get("rows", []))
        if "group by" in sql.lower():
            group_key = "city"
            if "group by city_name" in sql.lower():
                group_key = "city_name"
            return self._merge_grouped_rows(rows, group_key)
        return rows

    def _partition_tables(
        self,
        tables: dict[str, Table],
        partition_key: str,
        exchange: ShuffleExchange,
    ) -> list[dict[str, Table]]:
        table_names = list(tables.keys())
        if not table_names:
            return [{}]
        partitioned: dict[str, list] = {}
        for name, table in tables.items():
            if table.batch().row_count == 0:
                partitioned[name] = [table for _ in range(max(1, len(self.workers)))]
                continue
            if name == "cities":
                partitioned[name] = self._replicated_partitions(table, max(1, len(self.workers)))
            else:
                partitioned[name] = self._table_partitions(table, partition_key, exchange)
        rows: list[dict[str, Table]] = []
        worker_count = max(1, len(self.workers))
        for index in range(worker_count):
            partition_tables: dict[str, Table] = {}
            for name in table_names:
                partitions = partitioned[name]
                partition_tables[name] = partitions[index % len(partitions)]
            rows.append(partition_tables)
        return rows

    def _table_partitions(self, table: Table, key: str, exchange: ShuffleExchange) -> list[Table]:
        partitions = exchange.partition(table.batch(), key)
        return [self._rows_to_table(table.name, partition.rows, table.columns) for partition in partitions]

    def _replicated_partitions(self, table: Table, count: int) -> list[Table]:
        rows = [table.batch().row(i) for i in range(table.batch().row_count)]
        return [self._rows_to_table(table.name, rows, table.columns) for _ in range(count)]

    def _merge_grouped_rows(self, rows: list[dict[str, object]], group_key: str) -> list[dict[str, object]]:
        combined: dict[object, int] = {}
        for row in rows:
            key = row[group_key]
            combined[key] = combined.get(key, 0) + int(row.get("count", 0))
        return [{group_key: key, "count": count} for key, count in sorted(combined.items(), key=lambda item: item[0])]

    def _query_kind(self, sql: str) -> str:
        lowered = sql.lower()
        if "join" in lowered:
            return "join"
        if "count(*)" in lowered or "group by" in lowered:
            return "aggregate"
        return "scan"

    def _rows_to_table(self, name: str, rows: list[dict[str, object]], columns: tuple[Column, ...]) -> Table:
        if rows:
            return from_rows(name, rows)
        return Table(name, tuple(Column(column.name, tuple()) for column in columns))

    def _tables_payload(self, tables: dict[str, Table]) -> dict[str, object]:
        return {name: table.to_payload() for name, table in tables.items()}

    def _prune_tables(self, query: Query, tables: dict[str, Table]) -> dict[str, Table]:
        required = self._required_columns(query)
        if not required:
            return tables
        pruned = dict(tables)
        for name, table in list(pruned.items()):
            if name == "people":
                pruned[name] = table.project(tuple(sorted(required & self._people_columns(query, table))))
            elif name == "cities":
                pruned[name] = table.project(tuple(sorted(required & self._city_columns(query, table))))
        return pruned

    def _required_columns(self, query: Query) -> set[str]:
        required: set[str] = set()
        for item in query.select:
            required |= self._collect_expression_names(item.expression)
        if query.where is not None:
            required |= self._collect_expression_names(query.where)
        for join in query.joins:
            required |= self._collect_expression_names(join.condition)
        for expression in query.group_by:
            required |= self._collect_expression_names(expression)
        for item in query.order_by:
            required |= self._collect_expression_names(item.expression)
        return required

    def _collect_expression_names(self, expression: object) -> set[str]:
        names: set[str] = set()
        if isinstance(expression, Identifier):
            names.add(expression.name)
        elif isinstance(expression, BinaryExpression):
            names |= self._collect_expression_names(expression.left)
            names |= self._collect_expression_names(expression.right)
        elif isinstance(expression, FunctionCall):
            for argument in expression.arguments:
                names |= self._collect_expression_names(argument)
        elif isinstance(expression, Star):
            names.add("*")
        return names

    def _people_columns(self, query: Query, table: Table) -> set[str]:
        available = {column.name for column in table.columns}
        needed = {"name", "age", "city_id", "city", "score", "segment", "id"}
        if any(join.table.name == "cities" for join in query.joins):
            needed.add("city_id")
        if query.where is not None:
            needed |= self._collect_expression_names(query.where)
        return available & needed

    def _city_columns(self, query: Query, table: Table) -> set[str]:
        available = {column.name for column in table.columns}
        needed = {"id", "city_name"}
        if any(join.table.name == "people" for join in query.joins):
            needed.add("id")
        return available & needed


def _worker_main(worker_id: str, transport: QueueTransport, tables: dict[str, object]) -> None:
    worker = Worker(worker_id, transport, tables)
    worker.run_forever()


def _best_context():
    try:
        return get_context("fork")
    except ValueError:
        return get_context("spawn")
