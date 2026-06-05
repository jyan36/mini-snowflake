from __future__ import annotations

from dataclasses import dataclass

from sql_parser.ast import BinaryExpression, Identifier, Literal, Query, SelectItem, Star, TableRef


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    text: str


class ParseError(ValueError):
    pass


class Parser:
    def parse(self, sql: str) -> Query:
        self._tokens = self._tokenize(sql)
        self._position = 0
        query = self._parse_query()
        self._expect("EOF")
        return query

    def _parse_query(self) -> Query:
        self._expect_keyword("SELECT")
        select_items = self._parse_select_list()
        self._expect_keyword("FROM")
        source = TableRef(self._expect("IDENT").text)
        where = None
        if self._match_keyword("WHERE"):
            where = self._parse_expression()
        return Query(tuple(select_items), source, where)

    def _parse_select_list(self) -> list[SelectItem]:
        items = [SelectItem(self._parse_expression())]
        while self._match("COMMA"):
            items.append(SelectItem(self._parse_expression()))
        return items

    def _parse_expression(self):
        return self._parse_or()

    def _parse_or(self):
        expression = self._parse_and()
        while self._match_keyword("OR"):
            expression = BinaryExpression(expression, "OR", self._parse_and())
        return expression

    def _parse_and(self):
        expression = self._parse_comparison()
        while self._match_keyword("AND"):
            expression = BinaryExpression(expression, "AND", self._parse_comparison())
        return expression

    def _parse_comparison(self):
        left = self._parse_primary()
        if self._match("OP"):
            operator = self._previous().text
            if self._peek().kind == "OP" and self._peek().text == "=" and operator in {"<", ">"}:
                operator += self._advance().text
            right = self._parse_primary()
            return BinaryExpression(left, operator, right)
        return left

    def _parse_primary(self):
        if self._match("STAR"):
            return Star()
        token = self._advance()
        if token.kind == "IDENT":
            return Identifier(token.text)
        if token.kind == "NUMBER":
            return Literal(int(token.text))
        if token.kind == "STRING":
            return Literal(token.text)
        raise ParseError(f"unexpected token {token.kind}")

    def _tokenize(self, sql: str) -> list[Token]:
        tokens: list[Token] = []
        index = 0
        while index < len(sql):
            char = sql[index]
            if char.isspace():
                index += 1
                continue
            if char == ",":
                tokens.append(Token("COMMA", char))
                index += 1
                continue
            if char == "*":
                tokens.append(Token("STAR", char))
                index += 1
                continue
            if char in "=<>":
                tokens.append(Token("OP", char))
                index += 1
                continue
            if char == "'":
                end = sql.find("'", index + 1)
                if end == -1:
                    raise ParseError("unterminated string")
                tokens.append(Token("STRING", sql[index + 1 : end]))
                index = end + 1
                continue
            if char.isdigit():
                end = index + 1
                while end < len(sql) and sql[end].isdigit():
                    end += 1
                tokens.append(Token("NUMBER", sql[index:end]))
                index = end
                continue
            if char.isalpha() or char == "_":
                end = index + 1
                while end < len(sql) and (sql[end].isalnum() or sql[end] == "_"):
                    end += 1
                text = sql[index:end]
                kind = "IDENT"
                if text.upper() in {"AND", "OR", "AS"}:
                    kind = "IDENT"
                tokens.append(Token(kind, text))
                index = end
                continue
            raise ParseError(f"unexpected character {char!r}")
        tokens.append(Token("EOF", ""))
        return tokens

    def _match(self, kind: str) -> bool:
        if self._peek().kind != kind:
            return False
        self._position += 1
        return True

    def _match_keyword(self, keyword: str) -> bool:
        if self._peek().kind != "IDENT" or self._peek().text.upper() != keyword:
            return False
        self._position += 1
        return True

    def _expect(self, kind: str) -> Token:
        token = self._advance()
        if token.kind != kind:
            raise ParseError(f"expected {kind}, got {token.kind}")
        return token

    def _expect_keyword(self, keyword: str) -> Token:
        token = self._advance()
        if token.kind != "IDENT" or token.text.upper() != keyword:
            raise ParseError(f"expected {keyword}")
        return token

    def _peek(self) -> Token:
        return self._tokens[self._position]

    def _advance(self) -> Token:
        token = self._tokens[self._position]
        self._position += 1
        return token

    def _previous(self) -> Token:
        return self._tokens[self._position - 1]
