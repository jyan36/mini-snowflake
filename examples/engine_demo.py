from __future__ import annotations

from execution import ExecutionEngine
from planner import LogicalPlanner, Optimizer
from session import QuerySession
from sql_parser import Parser
from storage import from_rows


def main() -> None:
    session = QuerySession()

    sql = "select name from people where 1 = 1 and 2 = 2"
    raw = session.plan(sql)
    optimized = session.optimized_plan(sql)

    print("RAW PLAN")
    print(repr(raw))
    print()
    print("OPTIMIZED PLAN")
    print(repr(optimized))
    print()

    people = from_rows(
        "people",
        [
            {"name": "alice", "age": 10, "city": "seattle"},
            {"name": "bob", "age": 12, "city": "vancouver"},
            {"name": "carol", "age": 15, "city": "seattle"},
        ],
    )

    query = Parser().parse("select name, city from people where age >= 12 order by name")
    plan = Optimizer().optimize(LogicalPlanner().plan(query))
    rows = ExecutionEngine().execute(plan, {"people": people})

    print("QUERY RESULT")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()

