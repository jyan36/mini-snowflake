# Phase 4 Plan: Distributed Execution

## Goal
Run queries across a coordinator and multiple workers so the engine can dispatch tasks remotely, exchange shuffled data, and aggregate distributed results.

## Scope
- Introduce coordinator and worker roles
- Add a lightweight RPC protocol for task dispatch and result collection
- Implement partition exchange and shuffle for joins and aggregations
- Move from local parallelism to multi-process or multi-node distributed execution
- Preserve the current single-node and parallel local paths as fallbacks

## Distributed Strategy
- Coordinator: owns query planning, task splitting, assignment, retries, and result assembly
- Worker: receives tasks, executes scan/filter/join/aggregate fragments, returns partial results
- RPC transport: start with a simple local transport abstraction, then make it network-capable
- Shuffle: hash-partition intermediate rows by join/group keys and redistribute them to workers
- Result merge: combine worker outputs into the final client-visible rows

## Deliverables
- Coordinator and worker abstractions
- Task and result message types
- Shuffle exchange layer
- Distributed join and distributed aggregate execution
- Tests for dispatch, shuffle correctness, and result equivalence

## Exit Criteria
- A query can be decomposed into tasks and executed outside the coordinator process
- Shuffled joins and aggregations return the same rows as the local path
- Worker failures can be observed and retried at a basic level

## Multi-PR Plan

### PR 1: Coordinator and Worker Skeleton
- Add coordinator and worker classes
- Define task, result, and status messages
- Add a local in-process transport for development and tests
- Add tests for dispatch and result round-trips

### PR 2: RPC Transport and Task Execution
- Add request/response handling for scans and simple operators
- Serialize task payloads and result batches
- Add tests for transport error handling and successful round-trips

### PR 3: Shuffle Exchange Layer
- Implement hash partition exchange for distributed joins and group-bys
- Add shuffle write/read helpers for partitioned batches
- Add tests for partitioning correctness and bucket stability

### PR 4: Distributed Join and Aggregate Execution
- Execute join fragments on workers after shuffle
- Execute partial aggregates on workers and merge them at the coordinator
- Add tests comparing distributed vs local results

### PR 5: End-to-End Distributed Validation
- Run multi-stage distributed queries through the coordinator
- Add examples showing coordinator/worker behavior
- Document current limits and reliability assumptions

