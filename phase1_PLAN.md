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

## Multi-PR Plan

### PR 1: SQL Surface and AST
- Add tokens and a minimal parser for `SELECT`, `FROM`, and `WHERE`
- Define AST nodes for queries, projections, tables, and predicates
- Add parser tests for basic positive and negative cases

### PR 2: Logical Planning
- Translate the AST into a logical plan
- Add plan nodes for scan, filter, and projection
- Add tests that assert query shape for simple statements

### PR 3: Columnar Storage
- Introduce a small columnar table representation
- Add table metadata and batch-oriented row access
- Add a fixture dataset for exercising scans

### PR 4: Physical Execution
- Implement a batch scan operator
- Implement vectorized filter and projection operators
- Wire the operators into a simple physical plan executor

### PR 5: CLI and End-to-End Validation
- Update the CLI to parse, plan, and explain queries
- Add an end-to-end smoke path for a simple `SELECT` query
- Add documentation for the supported SQL subset and current limits
