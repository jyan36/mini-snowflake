import unittest

from tests import test_integration, test_query_matrix, test_sql_features


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None):  # noqa: D401
    suite = unittest.TestSuite()
    for module in (
        test_sql_features,
        test_integration,
        test_query_matrix,
    ):
        suite.addTests(loader.loadTestsFromModule(module))
    return suite

