# Tiny Distributed Query Engine Plan

## Objective
Build a compact distributed SQL query engine that showcases:
- SQL parsing and semantic analysis
- Query planning and cost-based optimization
- Columnar storage and vectorized execution
- Distributed execution with parallelism and fault recovery

This is a systems-level showcase project inspired by Tiny Spark, Tiny DuckDB, and Tiny Snowflake.

## Core Capabilities

### 1. SQL Parser
- Lexer + grammar for SQL SELECT, FROM, WHERE, GROUP BY, ORDER BY, JOIN, and simple DDL/CTE
- AST construction and validation
- Semantic analysis for names, types, and schemas

### 2. Query Planner
- Logical plan builder from SQL AST
- Rule-based rewrites for projection pushdown, filter pushdown, join reordering
- Physical plan generation with operator selection

### 3. Cost-Based Optimizer
- Statistics collection for tables and columns
- Cost model for I/O, CPU, and network transfer
- Join ordering planner using dynamic programming / greedy plan search
- Operator selection between hash join, sort-merge join, and broadcast join

### 4. Columnar Storage
- Columnar table format with batch-oriented columns
- Compressed page layout and vector-friendly batches
- Metadata for row counts, min/max, null counts
- Simple on-disk persistence for table files

### 5. Distributed Execution
- Cluster worker architecture with a coordinator and worker nodes
- Query decomposition into distributed tasks
- Remote task scheduling and result aggregation
- Shuffling and partition exchange for distributed joins and aggregations

### 6. Vectorized Operators
- Batch execution model operating on columnar vectors
- Vectorized scan, filter, projection, aggregate, and join operators
- Minimal materialization between operators

### 7. Parallel Joins
- Partitioned parallel hash join across worker nodes
- Multi-threaded build and probe stages
- Support for both local parallelism and distributed join execution

### 8. Fault Recovery
- Task-level retry for failed worker tasks
- Checkpointing of intermediate stages or result partitions
- Coordinator recovery logic for reassigning failed tasks

## Proposed Architecture

### Components
- `sql-parser/` — grammar, lexer, AST, semantic analyzer
- `planner/` — logical planner, optimizer, physical planner
- `storage/` — columnar format, metadata, on-disk table storage
- `execution/` — vectorized operators, local execution engine
- `distributed/` — cluster coordinator, worker RPC, shuffle layer
- `catalog/` — schema catalog and statistics

### Data Flow
1. SQL text -> Parser -> AST
2. AST -> Analyzer -> Logical plan
3. Logical plan -> Optimizer -> Physical plan
4. Physical plan -> Local/distributed execution
5. Results returned to client

## Phase Plan

### Phase 0: Foundation
- Initialize repository structure
- Add a `PLAN.md` with architecture and milestones
- Set up a small command-line harness or REPL

### Phase 1: Single-Node Core
- Implement parser and AST for SELECT/FROM/WHERE
- Build a logical plan and simple physical plan
- Add columnar storage and batch scan operator
- Implement vectorized filter and projection

### Phase 2: Optimization
- Add cost model and table statistics
- Implement rule-based pushdown rewrites
- Add join order optimization and physical join selection

### Phase 3: Parallel Local Execution
- Support multi-threaded execution within a single node
- Implement parallel hash join and aggregate
- Add local partitioning and parallel scan

### Phase 4: Distributed Execution
- Design coordinator and worker protocol
- Add RPC transport for task dispatch and result fetch
- Implement shuffle exchange and distributed join

### Phase 5: Reliability and Fault Recovery
- Add task retry and worker health checks
- Add checkpointing for intermediate shuffles
- Test failure scenarios with simulated worker crashes

### Phase 6: Demonstration and Use Cases
- Build end-to-end demos: TPC-H-style queries, join-heavy workloads, aggregation workloads
- Add performance comparisons for vectorized vs row-based execution
- Document architecture, limitations, and next steps

## Immediate Next Tasks
1. Create repository skeleton and module folders.
2. Write core SQL grammar and AST definitions.
3. Implement a small CLI that accepts SQL and prints a parsed plan.
4. Add a simple columnar table layout and scan operator.

## Success Criteria
- The system can parse and plan non-trivial SQL queries.
- It executes vectorized scans and joins on columnar data.
- It can schedule a query across multiple worker processes or nodes.
- It recovers from a failed worker task and completes the query.

---

> Note: This `PLAN.md` file is created locally in the repository workspace. No commit or push has been performed.
