from __future__ import annotations

import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from distributed import Coordinator
from execution import ExecutionEngine
from execution.scheduler import LocalScheduler
from planner import LogicalPlanner
from sql_parser import Parser
from storage import from_rows


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    sql: str


def build_people_table(size: int = 1000):
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


def benchmark_case(case: BenchmarkCase, people_table, cities_table) -> dict[str, object]:
    query = Parser().parse(case.sql)
    plan = LogicalPlanner().plan(query)

    sequential_engine = ExecutionEngine()
    parallel_engine = ExecutionEngine(scheduler=LocalScheduler(workers=2, batch_size=64))
    coordinator = Coordinator()
    worker_a = coordinator.register_worker("worker-a")
    worker_b = coordinator.register_worker("worker-b")
    worker_a.tables["people"] = people_table
    worker_a.tables["cities"] = cities_table
    worker_b.tables["people"] = people_table
    worker_b.tables["cities"] = cities_table

    sequential = _time_call(lambda: sequential_engine.execute(plan, {"people": people_table, "cities": cities_table}))
    parallel = _time_call(lambda: parallel_engine.execute(plan, {"people": people_table, "cities": cities_table}))
    distributed = _time_call(lambda: _run_distributed(coordinator, case.sql, people_table, cities_table))

    return {
        "name": case.name,
        "sequential_ms": sequential[0],
        "parallel_ms": parallel[0],
        "distributed_ms": distributed[0],
        "sequential_rows": len(sequential[1]),
        "parallel_rows": len(parallel[1]),
        "distributed_rows": len(distributed[1]),
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


def _time_call(fn):
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return elapsed_ms, result


def main(argv: list[str] | None = None) -> int:
    output = Path("benchmark_results.csv")
    cases = [
        BenchmarkCase("filter_projection", "select name from people where age >= 12"),
        BenchmarkCase("join", "select name, city_name from people join cities on city_id = id order by name"),
        BenchmarkCase("aggregate", "select city, count(*) from people group by city order by city"),
    ]
    people_table = build_people_table()
    cities_table = build_cities_table()

    results = [benchmark_case(case, people_table, cities_table) for case in cases]
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    for row in results:
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

