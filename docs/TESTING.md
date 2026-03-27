# Testing

## Local Setup

1. `python3 -m venv .venv`
2. `.venv/bin/pip install -e .[dev]`

## Commands

- Tests: `.venv/bin/pytest`
- Lint: `.venv/bin/ruff check .`
- Format check: `.venv/bin/ruff format --check .`
- Types: `.venv/bin/mypy src tests`

## Expected Coverage

- Schedule and home-game filtering
- Provider normalization
- MQTT topic and payload generation
- JSON state/cache logic
- Mocked end-to-end smoke path
