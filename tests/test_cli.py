import unittest

from session import QuerySession


class QuerySessionTest(unittest.TestCase):
    def test_explain_normalizes_sql(self) -> None:
        session = QuerySession()
        self.assertEqual(session.explain("select   1"), "unparsed query: select 1")
