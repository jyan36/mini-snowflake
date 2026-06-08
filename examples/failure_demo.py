from __future__ import annotations

from distributed import Coordinator


def main() -> None:
    coordinator = Coordinator()
    worker = coordinator.register_worker("worker-a")
    coordinator.refresh_health()

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    worker.execute = boom  # type: ignore[method-assign]
    try:
        coordinator.execute_with_retry("custom", {"value": 1}, retries=0)
    except Exception as exc:
        print(f"failure observed: {exc}")
        print(coordinator.worker_health["worker-a"])


if __name__ == "__main__":
    main()

