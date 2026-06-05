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

    def test_parse_select_star(self) -> None:
        query = Parser().parse("select * from people")
        self.assertEqual(query.select[0].expression.__class__.__name__, "Star")

    def test_parse_boolean_expression(self) -> None:
        query = Parser().parse("select name from people where age >= 10 and city = 'seattle'")
        self.assertEqual(query.where.operator, "AND")

    def test_parse_join_and_order(self) -> None:
        query = Parser().parse("select name from people join cities on city_id = id order by name desc")
        self.assertEqual(len(query.joins), 1)
        self.assertEqual(query.order_by[0].descending, True)

    def test_parse_cte(self) -> None:
        query = Parser().parse("with filtered as (select name from people) select name from filtered")
        self.assertEqual(query.ctes[0].name, "filtered")
