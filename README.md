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
## Notes

- The project is a showcase prototype, not a production SQL engine
- The distributed layer uses a local transport for now
- The benchmark numbers depend on your local machine and Python runtime
