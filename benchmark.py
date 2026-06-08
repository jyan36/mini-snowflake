from __future__ import annotations

import csv
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from distributed import Coordinator
from execution import ExecutionEngine, RowExecutor
from execution.scheduler import LocalScheduler
from planner import LogicalPlanner
from sql_parser import Parser
from storage import from_rows


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    sql: str


@dataclass(frozen=True)
class BenchmarkConfig:
    people_size: int = 50_000
    warmup_runs: int = 1
    sample_runs: int = 5


def build_people_table(size: int = 50_000):
    rows = []
    for index in range(size):
        rows.append(
            {
                "id": index + 1,
                "name": f"name-{index}",
                "age": 10 + (index % 50),
                "city_id": 100 if index % 2 == 0 else 200,
                "city": "seattle" if index % 2 == 0 else "vancouver",
            }
        )
    return from_rows("people", rows)


def build_cities_table():
    return from_rows(
        "cities",
        [
            {"id": 100, "city_name": "seattle"},
            {"id": 200, "city_name": "vancouver"},
        ],
    )


def benchmark_case(case: BenchmarkCase, people_table, cities_table, config: BenchmarkConfig | None = None) -> dict[str, object]:
    config = config or BenchmarkConfig()
    query = Parser().parse(case.sql)
    plan = LogicalPlanner().plan(query)

    row_executor = RowExecutor()
    sequential_engine = ExecutionEngine()
    parallel_engine = ExecutionEngine(scheduler=LocalScheduler(workers=2, batch_size=64))
    coordinator = Coordinator()
    worker_a = coordinator.register_worker("worker-a")
    worker_b = coordinator.register_worker("worker-b")
    worker_a.tables["people"] = people_table
    worker_a.tables["cities"] = cities_table
    worker_b.tables["people"] = people_table
    worker_b.tables["cities"] = cities_table

    row_based = _measure(lambda: row_executor.execute(plan, {"people": people_table, "cities": cities_table}), config)
    sequential = _measure(lambda: sequential_engine.execute(plan, {"people": people_table, "cities": cities_table}), config)
    parallel = _measure(lambda: parallel_engine.execute(plan, {"people": people_table, "cities": cities_table}), config)
    distributed = _measure(lambda: _run_distributed(coordinator, case.sql, people_table, cities_table), config)

    return {
        "name": case.name,
        "row_ms": row_based[0],
        "sequential_ms": sequential[0],
        "parallel_ms": parallel[0],
        "distributed_ms": distributed[0],
        "row_rows": row_based[1],
        "sequential_rows": sequential[1],
        "parallel_rows": parallel[1],
        "distributed_rows": distributed[1],
    }


def _run_distributed(coordinator: Coordinator, sql: str, people_table, cities_table):
    query = Parser().parse(sql)
    if "join" in sql.lower():
        rows = coordinator.distributed_join(
            [people_table.batch().row(i) for i in range(people_table.batch().row_count)],
            [cities_table.batch().row(i) for i in range(cities_table.batch().row_count)],
            "city_id",
            "id",
        )
        return rows
    if "count(*)" in sql.lower():
        rows = [people_table.batch().row(i) for i in range(people_table.batch().row_count)]
        return coordinator.distributed_count(rows, "city")
    return ExecutionEngine().execute(LogicalPlanner().plan(query), {"people": people_table, "cities": cities_table})


def _measure(fn, config: BenchmarkConfig):
    for _ in range(config.warmup_runs):
        result = fn()
    samples = []
    for _ in range(config.sample_runs):
        elapsed_ms, result = _time_call(fn)
        samples.append(elapsed_ms)
    return statistics.median(samples), len(result)


def _time_call(fn):
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return elapsed_ms, result


def main(argv: list[str] | None = None) -> int:
    output = Path("benchmark_results.csv")
    config = BenchmarkConfig()
    cases = [
        BenchmarkCase("filter_projection", "select name from people where age >= 12"),
        BenchmarkCase("join", "select name, city_name from people join cities on city_id = id order by name"),
        BenchmarkCase("aggregate", "select city, count(*) from people group by city order by city"),
    ]
    people_table = build_people_table(config.people_size)
    cities_table = build_cities_table()

    results = [benchmark_case(case, people_table, cities_table, config) for case in cases]
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    report = Path("benchmark_report.md")
    report.write_text(_render_report(results), encoding="utf-8")

    for row in results:
        print(row)

    return 0


def _render_report(results: list[dict[str, object]]) -> str:
    lines = ["# Benchmark Report", "", "| Case | Row | Sequential | Parallel | Distributed |", "| --- | ---: | ---: | ---: | ---: |"]
    for row in results:
        lines.append(
            f"| {row['name']} | {row['row_ms']:.3f} ms | {row['sequential_ms']:.3f} ms | {row['parallel_ms']:.3f} ms | {row['distributed_ms']:.3f} ms |"
        )
    lines.append("")
    lines.append("This report compares the row-based baseline with the vectorized, parallel, and distributed paths using median timings across repeated samples.")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
