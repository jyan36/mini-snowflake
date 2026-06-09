# Mini Snowflake

Mini Snowflake is a compact distributed SQL query engine prototype.

## How It Works

- SQL is parsed into an AST in `src/sql_parser/`
- Logical plans and optimizer rules live in `src/planner/`
- Columnar storage and batch tables live in `src/storage/`
- Vectorized execution lives in `src/execution/`
- Coordinator, workers, shuffle, and retry logic live in `src/distributed/`
- Schema statistics live in `src/catalog/`

## Run

```bash
python3 -m cli --sql "select 1"
```

```bash
python3 examples/engine_demo.py
```

```bash
python3 examples/distributed_demo.py
```

```bash
python3 examples/failure_demo.py
```

```bash
python3 benchmark.py
```

## Test

```bash
PYTHONPATH=src python3 -m unittest tests.unit_suite -q
```

```bash
PYTHONPATH=src python3 -m unittest tests.integration_suite -q
```

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

## Benchmark Output

- `benchmark.py` writes `benchmark_results.csv`
- It also writes `benchmark_report.md`
- The report compares row-based, vectorized, parallel, and distributed runs

# My Benchmark Results

# Benchmark Report

| Case | Row | Vectorized Sequential | Parallel | Distributed | Vectorized Sequential Speedup | Parallel Speedup | Distributed Speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| filter_projection | 86.932 ms | 50.753 ms | 90.973 ms | 76.707 ms | 1.71x | 0.96x | 1.13x |
| wide_projection | 129.017 ms | 121.935 ms | 149.892 ms | 148.181 ms | 1.06x | 0.86x | 0.87x |
| join | 179.928 ms | 150.685 ms | 170.857 ms | 136.826 ms | 1.19x | 1.05x | 1.32x |
| join_filter | 176.237 ms | 175.544 ms | 239.734 ms | 158.990 ms | 1.00x | 0.74x | 1.11x |
| aggregate | 93.747 ms | 41.205 ms | 136.158 ms | 56.598 ms | 2.28x | 0.69x | 1.66x |
| aggregate_filter | 108.889 ms | 76.645 ms | 158.956 ms | 82.546 ms | 1.42x | 0.69x | 1.32x |
| star_projection | 113.814 ms | 159.692 ms | 192.820 ms | 124.352 ms | 0.71x | 0.59x | 0.92x |

## Notes

- The project is a showcase prototype, not a production SQL engine
- The distributed layer uses a local transport for now
- The benchmark numbers depend on your local machine and Python runtime
