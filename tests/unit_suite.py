import unittest

from tests import (
    test_cost_model,
    test_execution,
    test_join_strategy,
    test_optimizer,
    test_parallel_aggregate,
    test_parallel_controls,
    test_parallel_join,
    test_parallel_scan,
    test_planner,
    test_rewrites,
    test_session,
    test_sql_parser,
    test_stats,
    test_storage,
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None):  # noqa: D401
    suite = unittest.TestSuite()
    for module in (
        test_sql_parser,
        test_planner,
        test_storage,
        test_execution,
        test_session,
        test_optimizer,
        test_rewrites,
        test_stats,
        test_join_strategy,
        test_cost_model,
        test_parallel_scan,
        test_parallel_join,
        test_parallel_aggregate,
        test_parallel_controls,
    ):
        suite.addTests(loader.loadTestsFromModule(module))
    return suite
