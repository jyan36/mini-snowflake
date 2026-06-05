# Phase 3 Plan: Parallel Local Execution

## Goal
Make a single node use multiple threads effectively for scans, joins, and aggregations while preserving the current logical/optimized planning flow.

## Scope
- Parallelize scans across row or batch partitions
- Add thread-safe local execution for joins and aggregations
- Introduce partitioning and merge steps for local parallel operators
- Keep the current optimizer and single-threaded path as the fallback
- Measure and surface basic execution parallelism in tests and examples

## Parallelization Strategy
- Partitioned scan: split table batches into fixed-size chunks and schedule them across workers/threads
- Parallel hash join: build per-partition hash tables, then merge probe results
- Parallel aggregate: partial aggregation per partition, then a final combine step
- Local partitioning: hash-partition rows on join/group keys before parallel operator execution
- Execution fallback: keep the existing sequential operators as the correctness baseline

## Deliverables
- Partition-aware execution primitives
- Parallel scan operator
- Parallel hash join operator
- Partial/final aggregation flow
- Tests for correctness and basic speedup/parallel behavior

## Exit Criteria
- Queries can run with multiple local workers/threads without changing results
- Parallel join and aggregate paths produce the same answers as the sequential path
- The engine can explain or log which operators were run in parallel

## Multi-PR Plan

### PR 1: Partitioned Scan and Scheduling
- Split table batches into partitions
- Add a simple local scheduler for dispatching partitions to threads
- Add tests that compare partitioned scan output to sequential scan output

### PR 2: Parallel Join Foundations
- Implement hash partitioning of left and right inputs on join keys
- Build per-partition hash tables and probe in parallel
- Add tests for correctness on small and skewed joins

### PR 3: Parallel Aggregation
- Add partial aggregation per partition
- Add a final combine phase for grouped results
- Add tests for grouped counts, sums, and mixed projections

### PR 4: Execution Controls and Observability
- Add a local execution mode switch for sequential vs parallel
- Surface worker count / partition count in explain or debug output
- Add tests that assert the chosen execution mode

### PR 5: End-to-End Parallel Validation
- Run join-heavy and aggregation-heavy queries through the parallel path
- Add example queries that show parallel execution behavior
- Document current limitations and correctness assumptions

