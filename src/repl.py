from __future__ import annotations

from session import QuerySession


def run_repl(session: QuerySession) -> int:
    print("mini-snowflake ready. Type SQL or 'exit'.")
    while True:
        try:
            line = input("sql> ").strip()
        except EOFError:
            print()
            return 0

        if not line:
            continue
        if line.lower() in {"exit", "quit"}:
            return 0

        print(session.explain(line))

