from __future__ import annotations

from distributed import Coordinator


def main() -> None:
    coordinator = Coordinator()
    coordinator.register_worker("worker-a")
    coordinator.register_worker("worker-b")

    left = [
        {"id": 1, "name": "alice", "city_id": 100},
        {"id": 2, "name": "bob", "city_id": 200},
        {"id": 3, "name": "carol", "city_id": 100},
    ]
    right = [
        {"id": 100, "city_name": "seattle"},
        {"id": 200, "city_name": "vancouver"},
    ]

    print("DISTRIBUTED JOIN")
    for row in coordinator.distributed_join(left, right, "city_id", "id"):
        print(row)

    print()
    print("DISTRIBUTED COUNT")
    for row in coordinator.distributed_count([{"city": "seattle"}, {"city": "vancouver"}, {"city": "seattle"}], "city"):
        print(row)


if __name__ == "__main__":
    main()

