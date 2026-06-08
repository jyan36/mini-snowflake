from __future__ import annotations

from dataclasses import dataclass

from catalog import StatsCatalog
from planner.cost import CostModel
from planner.logical import Aggregate, Filter, Join, LogicalPlan, Projection, Scan, Sort, With
from sql_parser.ast import BinaryExpression, Identifier, Literal, Query, SelectItem, Star


@dataclass(frozen=True)
class Optimizer:
    cost_model: CostModel = CostModel()
    stats: StatsCatalog | None = None

    def optimize(self, plan: LogicalPlan) -> LogicalPlan:
        if isinstance(plan, Projection):
            input_plan = self.optimize(plan.input)
            input_plan = self._pushdown_projection(input_plan, plan.expressions)
            if isinstance(input_plan, Projection):
                return Projection(input_plan.input, plan.expressions)
            return Projection(input_plan, plan.expressions)
        if isinstance(plan, Filter):
            input_plan = self.optimize(plan.input)
            predicate = self._fold(plan.predicate)
            if isinstance(input_plan, Projection):
                return Projection(Filter(input_plan.input, predicate), input_plan.expressions)
            return Filter(input_plan, predicate)
        if isinstance(plan, Aggregate):
            return Aggregate(self.optimize(plan.input), plan.group_by, plan.aggregates)
        if isinstance(plan, Sort):
            return Sort(self.optimize(plan.input), plan.order_by)
        if isinstance(plan, Join):
            left = self.optimize(plan.left)
            right = self.optimize(plan.right)
            strategy = self._choose_join_strategy(left, right)
            return Join(left, right, self._fold(plan.condition), strategy)
        if isinstance(plan, With):
            return With(tuple((name, self.optimize(cte_plan)) for name, cte_plan in plan.ctes), self.optimize(plan.input))
        return plan

    def _pushdown_projection(self, input_plan: LogicalPlan, expressions: tuple[object, ...]) -> LogicalPlan:
        if isinstance(input_plan, Filter):
            return Filter(self._pushdown_projection(input_plan.input, expressions), input_plan.predicate)
        if isinstance(input_plan, Join):
            required = self._required_columns(expressions)
            left_columns = self._columns_for(input_plan.left)
            right_columns = self._columns_for(input_plan.right)
            if required & left_columns:
                input_plan = Join(self._pushdown_projection(input_plan.left, tuple(Identifier(name) for name in sorted(required & left_columns))), self._pushdown_projection(input_plan.right, tuple(Identifier(name) for name in sorted(required & right_columns))), input_plan.condition)
            return input_plan
        return input_plan

    def _required_columns(self, expressions: tuple[object, ...]) -> set[str]:
        required: set[str] = set()
        for expression in expressions:
            if isinstance(expression, Identifier):
                required.add(expression.name)
            if isinstance(expression, BinaryExpression):
                required |= self._required_columns((expression.left, expression.right))
        return required

    def _columns_for(self, plan: LogicalPlan) -> set[str]:
        if isinstance(plan, Scan):
            return set()
        return set()

    def _fold(self, expression: object) -> object:
        if isinstance(expression, BinaryExpression):
            left = self._fold(expression.left)
            right = self._fold(expression.right)
            if isinstance(left, Literal) and isinstance(right, Literal):
                if expression.operator == "=":
                    return Literal(left.value == right.value)
                if expression.operator == "!=":
                    return Literal(left.value != right.value)
                if expression.operator == "<":
                    return Literal(left.value < right.value)
                if expression.operator == ">":
                    return Literal(left.value > right.value)
                if expression.operator == "<=":
                    return Literal(left.value <= right.value)
                if expression.operator == ">=":
                    return Literal(left.value >= right.value)
                if expression.operator == "AND":
                    return Literal(bool(left.value) and bool(right.value))
                if expression.operator == "OR":
                    return Literal(bool(left.value) or bool(right.value))
            return BinaryExpression(left, expression.operator, right)
        return expression

    def _choose_join_strategy(self, left: LogicalPlan, right: LogicalPlan) -> str:
        left_rows = self._estimate_rows(left)
        right_rows = self._estimate_rows(right)
        if min(left_rows, right_rows) <= 100:
            return "broadcast"
        if left_rows + right_rows > 10_000:
            return "sort_merge"
        return "hash"

    def _estimate_rows(self, plan: LogicalPlan) -> float:
        if isinstance(plan, Scan) and self.stats is not None:
            table = self.stats.get(plan.table)
            if table is not None:
                return float(table.row_count)
        return self.cost_model.estimate(plan).rows

    def optimize_query(self, query: Query) -> Query:
        select_items = tuple(self._optimize_select_item(item) for item in query.select)
        return Query(select_items, query.source, query.where, query.joins, query.group_by, query.order_by, query.ctes)

    def _optimize_select_item(self, item: SelectItem) -> SelectItem:
        if isinstance(item.expression, Star):
            return item
        return item
