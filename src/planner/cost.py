from __future__ import annotations

from dataclasses import dataclass

from planner.logical import Aggregate, Filter, Join, LogicalPlan, Projection, Scan, Sort, With


@dataclass(frozen=True)
class CostEstimate:
    rows: float
    cpu: float
    io: float
    network: float = 0.0

    @property
    def total(self) -> float:
        return self.cpu + self.io + self.network


@dataclass(frozen=True)
class CostModel:
    scan_cost: float = 1.0
    filter_cost: float = 0.25
    projection_cost: float = 0.1
    join_cost: float = 3.0
    aggregate_cost: float = 1.5
    sort_cost: float = 2.0

    def estimate(self, plan: LogicalPlan, input_rows: float = 1000.0) -> CostEstimate:
        if isinstance(plan, Scan):
            return CostEstimate(input_rows, input_rows * self.scan_cost, input_rows * 0.5)
        if isinstance(plan, Filter):
            child = self.estimate(plan.input, input_rows)
            rows = child.rows * 0.5
            return CostEstimate(rows, child.cpu + rows * self.filter_cost, child.io)
        if isinstance(plan, Projection):
            child = self.estimate(plan.input, input_rows)
            return CostEstimate(child.rows, child.cpu + child.rows * self.projection_cost, child.io)
        if isinstance(plan, Join):
            left = self.estimate(plan.left, input_rows)
            right = self.estimate(plan.right, input_rows)
            rows = max(left.rows, right.rows)
            return CostEstimate(rows, left.cpu + right.cpu + rows * self.join_cost, left.io + right.io, left.rows + right.rows)
        if isinstance(plan, Aggregate):
            child = self.estimate(plan.input, input_rows)
            rows = max(1.0, child.rows * 0.1)
            return CostEstimate(rows, child.cpu + rows * self.aggregate_cost, child.io)
        if isinstance(plan, Sort):
            child = self.estimate(plan.input, input_rows)
            return CostEstimate(child.rows, child.cpu + child.rows * self.sort_cost, child.io)
        if isinstance(plan, With):
            child = self.estimate(plan.input, input_rows)
            return CostEstimate(child.rows, child.cpu, child.io)
        return CostEstimate(input_rows, input_rows, input_rows)
