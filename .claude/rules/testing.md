# Testing

## Framework

Use `pytest` for all tests. The project includes it in the `[dev]` optional deps:

```bash
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/                          # all tests
pytest tests/test_file.py              # single file
pytest tests/test_file.py::test_name   # single test
pytest -xsv tests/                     # verbose, stop on first failure
```

## Test location

Place tests under `tests/` mirroring the module path. New env adapters should have smoke tests that verify:

1. DataLoader can load the split
2. `build_train_env` / `build_eval_env` return correct item lists
3. `process_one` produces valid results for at least one sample item
4. The end-to-end pipeline (6 stages) completes for a mini-run

## Test data

Keep small fixture datasets (1-3 items) in `tests/fixtures/`. Never commit real benchmark datasets.
