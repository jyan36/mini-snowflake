from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Query:
    select: tuple["SelectItem", ...]
    source: "TableRef"
    where: "Expression | None" = None


@dataclass(frozen=True, slots=True)
class SelectItem:
    expression: "Expression"
    alias: str | None = None


@dataclass(frozen=True, slots=True)
class TableRef:
    name: str


class Expression:
    pass


@dataclass(frozen=True, slots=True)
class Identifier(Expression):
    name: str


@dataclass(frozen=True, slots=True)
class Star(Expression):
    pass


@dataclass(frozen=True, slots=True)
class Literal(Expression):
    value: Any


@dataclass(frozen=True, slots=True)
class BinaryExpression(Expression):
    left: Expression
    operator: str
    right: Expression
