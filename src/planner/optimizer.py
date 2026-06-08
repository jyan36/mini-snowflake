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
            input_plan = self._pushdown_projection(input_plan, self._required_columns(plan.expressions))
            return Projection(input_plan, plan.expressions)
        if isinstance(plan, Filter):
            input_plan = self.optimize(plan.input)
            predicate = self._fold(plan.predicate)
            return self._pushdown_filter(input_plan, predicate)
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

    def _pushdown_projection(self, input_plan: LogicalPlan, required: set[str]) -> LogicalPlan:
        if not required:
            return input_plan
        if isinstance(input_plan, Projection):
            inner_required = required | self._required_columns(input_plan.expressions)
            return Projection(self._pushdown_projection(input_plan.input, inner_required), input_plan.expressions)
        if isinstance(input_plan, Filter):
            inner_required = required | self._required_columns((input_plan.predicate,))
            return Filter(self._pushdown_projection(input_plan.input, inner_required), input_plan.predicate)
        if isinstance(input_plan, Join):
            join_required = required | self._required_columns((input_plan.condition,))
            left_required = self._required_columns_for_branch(input_plan.left, join_required)
            right_required = self._required_columns_for_branch(input_plan.right, join_required)
            return Join(
                self._pushdown_projection(input_plan.left, left_required),
                self._pushdown_projection(input_plan.right, right_required),
                input_plan.condition,
                input_plan.strategy,
            )
        if isinstance(input_plan, Aggregate):
            inner_required = required | self._required_columns(input_plan.group_by + input_plan.aggregates)
            return Aggregate(self._pushdown_projection(input_plan.input, inner_required), input_plan.group_by, input_plan.aggregates)
        if isinstance(input_plan, Sort):
            inner_required = required | self._required_columns(input_plan.order_by)
            return Sort(self._pushdown_projection(input_plan.input, inner_required), input_plan.order_by)
        if isinstance(input_plan, Scan):
            return Projection(input_plan, tuple(Identifier(name) for name in sorted(required)))
        return input_plan

    def _pushdown_filter(self, input_plan: LogicalPlan, predicate: object) -> LogicalPlan:
        if isinstance(input_plan, Projection):
            return Projection(self._pushdown_filter(input_plan.input, predicate), input_plan.expressions)
        if isinstance(input_plan, Join):
            return Filter(input_plan, predicate)
        return Filter(input_plan, predicate)

    def _required_columns(self, expressions: tuple[object, ...]) -> set[str]:
        required: set[str] = set()
        for expression in expressions:
            if isinstance(expression, Identifier):
                required.add(expression.name)
            if isinstance(expression, BinaryExpression):
                required |= self._required_columns((expression.left, expression.right))
            if isinstance(expression, FunctionCall):
                required |= self._required_columns(expression.arguments)
        return required

    def _required_columns_for_branch(self, plan: LogicalPlan, required: set[str]) -> set[str]:
        if isinstance(plan, Scan):
            return set(required)
        if isinstance(plan, Projection):
            return self._required_columns(plan.expressions) | required
        if isinstance(plan, Filter):
            return self._required_columns((plan.predicate,)) | required
        if isinstance(plan, Join):
            return self._required_columns((plan.condition,)) | required
        if isinstance(plan, Aggregate):
            return self._required_columns(plan.group_by + plan.aggregates) | required
        if isinstance(plan, Sort):
            return self._required_columns(plan.order_by) | required
        return set(required)

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
