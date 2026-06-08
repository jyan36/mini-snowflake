from __future__ import annotations

from workload import build_demo_workload


def main() -> None:
    for case in build_demo_workload():
        print(f"{case.name}: {case.sql}")


if __name__ == "__main__":
    main()
