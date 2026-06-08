from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkloadCase:
    name: str
    sql: str


def build_demo_workload() -> list[WorkloadCase]:
    return [
        WorkloadCase("filter_projection", "select name from people where age >= 12"),
        WorkloadCase("join", "select name, city_name from people join cities on city_id = id order by name"),
        WorkloadCase("aggregate", "select city, count(*) from people group by city order by city"),
    ]

