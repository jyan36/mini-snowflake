from __future__ import annotations

from dataclasses import dataclass

from planner.logical import Aggregate, Filter, Join, LogicalPlan, Projection, Scan, Sort, With
from sql_parser.ast import BinaryExpression, Literal


@dataclass(frozen=True, slots=True)
class Optimizer:
    def optimize(self, plan: LogicalPlan) -> LogicalPlan:
        if isinstance(plan, Projection):
            input_plan = self.optimize(plan.input)
            if isinstance(input_plan, Projection):
                return Projection(input_plan.input, plan.expressions)
            return Projection(input_plan, plan.expressions)
        if isinstance(plan, Filter):
            input_plan = self.optimize(plan.input)
            return Filter(input_plan, self._fold(plan.predicate))
        if isinstance(plan, Aggregate):
            return Aggregate(self.optimize(plan.input), plan.group_by, plan.aggregates)
        if isinstance(plan, Sort):
            return Sort(self.optimize(plan.input), plan.order_by)
        if isinstance(plan, Join):
            return Join(self.optimize(plan.left), self.optimize(plan.right), self._fold(plan.condition))
        if isinstance(plan, With):
            return With(tuple((name, self.optimize(cte_plan)) for name, cte_plan in plan.ctes), self.optimize(plan.input))
        return plan

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

