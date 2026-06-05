import unittest

from session import QuerySession


class QuerySessionTest(unittest.TestCase):
    def test_explain_returns_plan(self) -> None:
        session = QuerySession()
        output = session.explain("select name from people where age = 10")
        self.assertIn("Projection", output)
        self.assertIn("Filter", output)
        self.assertIn("Scan", output)

