from __future__ import annotations

import csv
import argparse
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from distributed import Coordinator, ProcessWorkerPool
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
    people_size: int = 500_000
    warmup_runs: int = 1
    sample_runs: int = 3


def build_people_table(size: int = 500_000):
    rows = []
    for index in range(size):
        rows.append(
            {
                "id": index + 1,
                "name": f"name-{index}",
                "age": 10 + (index % 50),
                "city_id": 100 if index % 2 == 0 else 200,
                "city": "seattle" if index % 2 == 0 else "vancouver",
                "score": (index * 17) % 10_000,
                "segment": f"segment-{index % 8}",
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
    process_pool = ProcessWorkerPool()
    process_pool.add_worker("worker-a", {"people": people_table, "cities": cities_table})
    process_pool.add_worker("worker-b", {"people": people_table, "cities": cities_table})

    row_based = _measure(lambda: row_executor.execute(plan, {"people": people_table, "cities": cities_table}), config)
    sequential = _measure(lambda: sequential_engine.execute(plan, {"people": people_table, "cities": cities_table}), config)
    parallel = _measure(lambda: parallel_engine.execute(plan, {"people": people_table, "cities": cities_table}), config)
    distributed = _measure(lambda: _run_distributed(coordinator, case.sql, people_table, cities_table), config)
    process_distributed = (
        _measure(lambda: _run_distributed_process_pool(process_pool, case.sql, people_table, cities_table), config)
        if _supports_process_distributed(case.sql)
        else distributed
    )
    process_pool.stop_all()

    return {
        "name": case.name,
        "row_ms": row_based[0],
        "sequential_ms": sequential[0],
        "parallel_ms": parallel[0],
        "distributed_ms": distributed[0],
        "process_distributed_ms": process_distributed[0],
        "row_speedup": _speedup(row_based[0], sequential[0]),
        "parallel_speedup": _speedup(row_based[0], parallel[0]),
        "distributed_speedup": _speedup(row_based[0], distributed[0]),
        "process_distributed_speedup": _speedup(row_based[0], process_distributed[0]),
        "row_rows": row_based[1],
        "sequential_rows": sequential[1],
        "parallel_rows": parallel[1],
        "distributed_rows": distributed[1],
        "process_distributed_rows": process_distributed[1],
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


def _run_distributed_process_pool(process_pool: ProcessWorkerPool, sql: str, people_table, cities_table):
    if "join" in sql.lower():
        return process_pool.distributed_join(
            [people_table.batch().row(i) for i in range(people_table.batch().row_count)],
            [cities_table.batch().row(i) for i in range(cities_table.batch().row_count)],
            "city_id",
            "id",
        )
    if "count(*)" in sql.lower():
        return process_pool.distributed_count(
            [people_table.batch().row(i) for i in range(people_table.batch().row_count)],
            "city",
        )
    return ExecutionEngine().execute(LogicalPlanner().plan(Parser().parse(sql)), {"people": people_table, "cities": cities_table})


def _supports_process_distributed(sql: str) -> bool:
    lowered = sql.lower()
    return "join" in lowered or "count(*)" in lowered


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
    args = _parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "benchmark_results.csv"
    config = BenchmarkConfig(
        people_size=args.people_size,
        warmup_runs=args.warmup_runs,
        sample_runs=args.sample_runs,
    )
    cases = [
        BenchmarkCase("filter_projection", "select name from people where age >= 12"),
        BenchmarkCase("wide_projection", "select id, name, age, city, score from people where age >= 20 and score >= 5000 order by score"),
        BenchmarkCase("join", "select name, city_name from people join cities on city_id = id order by name"),
        BenchmarkCase("join_filter", "select name, city_name from people join cities on city_id = id where age >= 25 and score >= 5000 order by name"),
        BenchmarkCase("aggregate", "select city, count(*) from people group by city order by city"),
        BenchmarkCase("aggregate_filter", "select city, count(*) from people where score >= 2500 group by city order by city"),
        BenchmarkCase("star_projection", "select * from people where age >= 30 order by score"),
    ]
    people_table = build_people_table(config.people_size)
    cities_table = build_cities_table()

    results = [benchmark_case(case, people_table, cities_table, config) for case in cases]
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    report = output_dir / "benchmark_report.md"
    report.write_text(_render_report(results), encoding="utf-8")

    for row in results:
        print(row)

    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark the query engine")
    parser.add_argument("--people-size", type=int, default=BenchmarkConfig.people_size)
    parser.add_argument("--warmup-runs", type=int, default=BenchmarkConfig.warmup_runs)
    parser.add_argument("--sample-runs", type=int, default=BenchmarkConfig.sample_runs)
    parser.add_argument("--output-dir", type=str, default="benchmark_out")
    return parser.parse_args(argv)


def _render_report(results: list[dict[str, object]]) -> str:
    lines = [
        "# Benchmark Report",
        "",
        "| Case | Row | Sequential | Parallel | Distributed | Row Speedup | Parallel Speedup | Distributed Speedup |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in results:
        lines.append(
            f"| {row['name']} | {row['row_ms']:.3f} ms | {row['sequential_ms']:.3f} ms | {row['parallel_ms']:.3f} ms | {row['distributed_ms']:.3f} ms | "
            f"{row['row_speedup']:.2f}x | {row['parallel_speedup']:.2f}x | {row['distributed_speedup']:.2f}x |"
        )
    lines.append("")
    lines.append("This report compares the row-based baseline with the vectorized, parallel, and distributed paths using median timings across repeated samples.")
    return "\n".join(lines)


def _speedup(baseline_ms: float, other_ms: float) -> float:
    if other_ms <= 0:
        return float("inf")
    return baseline_ms / other_ms


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
