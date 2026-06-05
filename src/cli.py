from __future__ import annotations

import argparse
import sys

from repl import run_repl
from session import QuerySession


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mini-snowflake")
    parser.add_argument("--sql", help="Run a single SQL statement and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session = QuerySession()

    if args.sql:
        result = session.explain(args.sql)
        print(result)
        return 0

    return run_repl(session)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

