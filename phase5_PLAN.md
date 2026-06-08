# Phase 5 Plan: Reliability and Fault Recovery

## Goal
Make the engine measurable and resilient by adding benchmarks, health checks, retries, and checkpoint-based recovery for distributed work.

## Scope
- Add a repeatable benchmark harness for sequential, parallel, and distributed execution
- Add worker health checks and coordinator-side liveness tracking
- Retry failed tasks on another worker when possible
- Persist and restore intermediate shuffle state
- Simulate worker failure scenarios and validate recovery behavior

## Reliability Strategy
- Benchmark first: make performance visible before changing recovery logic
- Health tracking: coordinator monitors worker responsiveness and marks unhealthy workers
- Retry policy: reassign failed tasks with simple bounded retries
- Checkpointing: save shuffle partitions or partial outputs so a query can resume
- Failure injection: test crash/retry paths with deterministic simulated failures

## Deliverables
- Benchmark runner with CSV/JSON output
- Heartbeat and worker health reporting
- Task retry and worker reassignment
- Shuffle checkpoint read/write helpers
- Failure simulation tests and recovery validation

## Exit Criteria
- A benchmark run can compare sequential, parallel, and distributed timings
- Failed workers can be detected and retried
- A query can resume from a saved checkpoint in at least one stage
- Recovery behavior is verified by tests

## Multi-PR Plan

### PR 1: Benchmark Harness
- Add a benchmark runner script
- Measure scan, filter, join, and aggregate timings
- Compare sequential, parallel, and distributed modes
- Output results to console and optional CSV or JSON

### PR 2: Worker Health Checks
- Add heartbeats or liveness probes from coordinator to workers
- Track healthy, unhealthy, and stale worker states
- Add tests for missing heartbeat behavior

### PR 3: Task Retry and Reassignment
- Retry failed tasks on a different worker
- Cap retries and surface failure status cleanly
- Add tests that simulate one worker failing mid-task

### PR 4: Shuffle Checkpointing
- Persist shuffle partitions or partial outputs
- Add checkpoint restore helpers for restart scenarios
- Add tests for resume-from-checkpoint behavior

### PR 5: Failure Simulation and Validation
- Add failure-injection demos or tests
- Validate recovered results against baseline outputs
- Document limitations and operational assumptions

