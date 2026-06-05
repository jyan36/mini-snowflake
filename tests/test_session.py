import unittest

from session import QuerySession


class QuerySessionTest(unittest.TestCase):
    def test_raw_and_optimized_plan_differ(self) -> None:
        session = QuerySession()
        sql = "select name from people where 1 = 1 and 2 = 2"

        raw = session.plan(sql)
        optimized = session.optimized_plan(sql)

        self.assertNotEqual(repr(raw), repr(optimized))
        self.assertIn("Literal(value=True)", repr(optimized))

    def test_explain_returns_plan(self) -> None:
        session = QuerySession()
        output = session.explain("select name from people where age = 10")
        self.assertIn("Projection", output)
        self.assertIn("Filter", output)
        self.assertIn("Scan", output)
