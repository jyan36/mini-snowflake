from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from sql_parser.ast import BinaryExpression, FunctionCall, Identifier, Star
from storage import Batch, Table


class LocalScheduler:
    def __init__(self, workers: int = 1, batch_size: int = 4096) -> None:
        self.workers = max(1, workers)
        self.batch_size = max(1, batch_size)

    def scan(self, table: Table) -> Batch:
        batches = table.partitioned_batches(self.batch_size)
        if self.workers == 1 or len(batches) <= 1:
            return self._merge_batches(batches)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            results = list(pool.map(lambda batch: batch, batches))
        return self._merge_batches(results)

    def join(self, left: Batch, right: Batch, condition: object) -> Batch:
        key_pair = self._join_keys(condition)
        if key_pair is None or self.workers == 1:
            from execution.operators import JoinOperator

            return JoinOperator(condition).execute(left, right)
        left_key, right_key = key_pair
        partitions = max(1, min(self.workers, left.row_count or 1, right.row_count or 1))
        left_rows = [left.row(i) for i in range(left.row_count)]
        right_rows = [right.row(i) for i in range(right.row_count)]
        left_parts = self._partition_rows(left_rows, left_key, partitions)
        right_parts = self._partition_rows(right_rows, right_key, partitions)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            results = list(
                pool.map(
                    lambda item: self._join_partition(item[0], item[1], left_key, right_key),
                    zip(left_parts, right_parts),
                )
            )
        rows = [row for partition in results for row in partition]
        return self._rows_to_batch(rows)

    def aggregate(self, batch: Batch, group_by: tuple[object, ...], aggregates: tuple[object, ...]) -> Batch:
        rows = [batch.row(i) for i in range(batch.row_count)]
        if self.workers == 1 or len(rows) <= self.batch_size:
            from execution.operators import AggregateOperator

            return AggregateOperator(group_by, aggregates).execute(batch)
        partitions = max(1, min(self.workers, len(rows)))
        buckets = self._partition_aggregate_rows(rows, partitions, group_by)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            partials = list(pool.map(lambda bucket: self._aggregate_bucket(bucket, group_by, aggregates), buckets))
        combined_rows = self._combine_aggregates(partials, group_by, aggregates)
        return self._rows_to_batch(combined_rows)

    def _merge_batches(self, batches: list[Batch]) -> Batch:
        if not batches:
            return Batch(())
        if len(batches) == 1:
            return batches[0]
        names = tuple(column.name for column in batches[0].columns)
        columns = []
        for index, name in enumerate(names):
            values = tuple(value for batch in batches for value in batch.columns[index].values)
            columns.append(batches[0].columns[index].__class__(name, values))
        return Batch(tuple(columns))

    def _join_keys(self, condition: object) -> tuple[str, str] | None:
        if isinstance(condition, BinaryExpression) and condition.operator == "=":
            if isinstance(condition.left, Identifier) and isinstance(condition.right, Identifier):
                return condition.left.name, condition.right.name
        return None

    def _partition_rows(self, rows: list[dict[str, object]], key: str, partitions: int) -> list[list[dict[str, object]]]:
        buckets = [[] for _ in range(partitions)]
        for row in rows:
            buckets[hash(row[key]) % partitions].append(row)
        return buckets

    def _join_partition(
        self,
        left_rows: list[dict[str, object]],
        right_rows: list[dict[str, object]],
        left_key: str,
        right_key: str,
    ) -> list[dict[str, object]]:
        hash_table: dict[object, list[dict[str, object]]] = {}
        for row in left_rows:
            hash_table.setdefault(row[left_key], []).append(row)
        results = []
        for row in right_rows:
            for left_row in hash_table.get(row[right_key], []):
                results.append({**left_row, **row})
        return results

    def _rows_to_batch(self, rows: list[dict[str, object]]) -> Batch:
        if not rows:
            return Batch(())
        names = tuple(rows[0].keys())
        from storage import Column

        return Batch(tuple(Column(name, tuple(row[name] for row in rows)) for name in names))

    def _name(self, expression: object) -> str:
        if isinstance(expression, Identifier):
            return expression.name
        if isinstance(expression, FunctionCall):
            return expression.name.lower()
        return "expr"

    def _partition_aggregate_rows(
        self,
        rows: list[dict[str, object]],
        partitions: int,
        group_by: tuple[object, ...],
    ) -> list[list[dict[str, object]]]:
        buckets = [[] for _ in range(partitions)]
        for row in rows:
            key = tuple(self._evaluate(expression, row) for expression in group_by)
            buckets[hash(key) % partitions].append(row)
        return buckets

    def _aggregate_bucket(
        self,
        rows: list[dict[str, object]],
        group_by: tuple[object, ...],
        aggregates: tuple[object, ...],
    ) -> list[dict[str, object]]:
        if not rows:
            return []
        groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
        for row in rows:
            key = tuple(self._evaluate(expression, row) for expression in group_by)
            groups.setdefault(key, []).append(row)
        partial_rows = []
        for key, grouped_rows in groups.items():
            row = {}
            for index, expression in enumerate(group_by):
                row[self._name(expression)] = key[index]
            for expression in aggregates:
                row[self._name(expression)] = self._partial_aggregate(expression, grouped_rows)
            partial_rows.append(row)
        return partial_rows

    def _combine_aggregates(
        self,
        partials: list[list[dict[str, object]]],
        group_by: tuple[object, ...],
        aggregates: tuple[object, ...],
    ) -> list[dict[str, object]]:
        combined: dict[tuple[object, ...], list[dict[str, object]]] = {}
        for partition in partials:
            for row in partition:
                key = tuple(row[self._name(expression)] for expression in group_by)
                combined.setdefault(key, []).append(row)
        final_rows = []
        for key, grouped_rows in combined.items():
            row = {}
            for index, expression in enumerate(group_by):
                row[self._name(expression)] = key[index]
            for expression in aggregates:
                row[self._name(expression)] = self._final_aggregate(expression, grouped_rows)
            final_rows.append(row)
        return final_rows

    def _partial_aggregate(self, expression: object, rows: list[dict[str, object]]) -> object:
        if isinstance(expression, FunctionCall):
            name = expression.name.lower()
            if name == "count":
                return len(rows)
            if name == "sum":
                return sum(self._evaluate(expression.arguments[0], row) for row in rows)
            if name == "min":
                return min(self._evaluate(expression.arguments[0], row) for row in rows)
            if name == "max":
                return max(self._evaluate(expression.arguments[0], row) for row in rows)
        if isinstance(expression, Identifier):
            return self._evaluate(expression, rows[0])
        raise ValueError(f"unsupported partial aggregate {expression!r}")

    def _final_aggregate(self, expression: object, rows: list[dict[str, object]]) -> object:
        if isinstance(expression, FunctionCall):
            name = expression.name.lower()
            if name == "count":
                return sum(row[self._name(expression)] for row in rows)
            if name == "sum":
                return sum(row[self._name(expression)] for row in rows)
            if name == "min":
                return min(row[self._name(expression)] for row in rows)
            if name == "max":
                return max(row[self._name(expression)] for row in rows)
            if expression.arguments == (Star(),):
                return sum(row[self._name(expression)] for row in rows)
        if isinstance(expression, Identifier):
            return rows[0][self._name(expression)]
        raise ValueError(f"unsupported final aggregate {expression!r}")

    def _evaluate(self, expression: object, row: dict[str, object]) -> object:
        if isinstance(expression, Identifier):
            return row[expression.name]
        if isinstance(expression, BinaryExpression):
            left = self._evaluate(expression.left, row)
            right = self._evaluate(expression.right, row)
            if expression.operator == "=":
                return left == right
            if expression.operator == "!=":
                return left != right
            if expression.operator == "<":
                return left < right
            if expression.operator == ">":
                return left > right
            if expression.operator == "<=":
                return left <= right
            if expression.operator == ">=":
                return left >= right
            if expression.operator == "AND":
                return bool(left) and bool(right)
            if expression.operator == "OR":
                return bool(left) or bool(right)
        if isinstance(expression, FunctionCall):
            return self._name(expression)
        raise ValueError(f"unsupported group expression {expression!r}")
