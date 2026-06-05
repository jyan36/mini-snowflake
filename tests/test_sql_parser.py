import unittest

from sql_parser import BinaryExpression, Identifier, Literal, ParseError, Parser


class ParserTest(unittest.TestCase):
    def test_parse_select_from_where(self) -> None:
        query = Parser().parse("select name from people where age = 10")
        self.assertEqual(query.source.name, "people")
        self.assertEqual(len(query.select), 1)
        self.assertEqual(query.select[0].expression, Identifier("name"))
        self.assertEqual(
            query.where,
            BinaryExpression(Identifier("age"), "=", Literal(10)),
        )

    def test_parse_rejects_unknown_token(self) -> None:
        with self.assertRaises(ParseError):
            Parser().parse("select @ from people")

