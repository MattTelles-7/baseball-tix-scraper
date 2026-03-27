# Testing

## Local Setup

1. `python3 -m venv .venv`
2. `.venv/bin/pip install -e .[dev]`

## Commands

- Tests: `.venv/bin/pytest`
- Lint: `.venv/bin/ruff check .`
- Format check: `.venv/bin/ruff format --check .`
- Types: `.venv/bin/mypy src tests`

## What The Tests Cover

- Team resolution and MLB schedule normalization
- Home-game filtering and grace-window retention
- JSON state persistence and dedupe bookkeeping
- MQTT topic, unique ID, and discovery payload generation
- Ticketmaster matching and `priceRanges.min` normalization
- A mocked service-path smoke test

## Notes

- The test suite is fully mocked and does not require live Ticketmaster, MQTT, or Home Assistant access.
- If you add any live checks later, gate them behind explicit flags or env vars and keep them out of the default CI path.
