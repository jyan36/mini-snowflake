# Phase 1 Plan: Single-Node Core

## Goal
Build the first runnable single-node SQL engine path.

## Scope
- Parse `SELECT`, `FROM`, and `WHERE`
- Build a logical plan from the parsed SQL
- Produce a simple physical plan for execution
- Add columnar table storage and a batch scan operator
- Implement vectorized filter and projection operators

## Deliverables
- SQL AST for basic queries
- Logical and physical plan structures
- Minimal columnar storage layer
- CLI path that can accept SQL and explain the plan

## Exit Criteria
- Basic queries can be parsed and planned
- A query can scan columnar data and apply filter/projection in batches

