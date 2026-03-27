# AGENTS.md

## Purpose

Build and operate a single-user service that tracks MLB home-game ticket prices and publishes them into Home Assistant through MQTT discovery.

## Required Reading

Read this file first, then read the docs relevant to the task before making changes:

1. `README.md`
2. `PLANS.md`
3. `docs/PRODUCT.md`
4. `docs/ARCHITECTURE.md`
5. `docs/SOURCES.md`
6. `docs/OPERATIONS.md`
7. `docs/HOME_ASSISTANT.md`
8. `docs/TESTING.md`

## Commands

- Create venv: `python3 -m venv .venv`
- Install dev deps: `.venv/bin/pip install -e .[dev]`
- Run tests: `.venv/bin/pytest`
- Lint: `.venv/bin/ruff check .`
- Format check: `.venv/bin/ruff format --check .`
- Type check: `.venv/bin/mypy src tests`

## Conventions

- Python 3.12+.
- Keep modules small and typed.
- Prefer official/public APIs over scraping.
- Keep Home Assistant entity IDs and MQTT topics deterministic.
- Persist only lightweight JSON state in `DATA_DIR`.
- Update docs with code changes.

## Do-Not Rules

- Do not add SQL as a v1 dependency.
- Do not add anti-bot evasion, CAPTCHA handling, proxy rotation, or Cloudflare bypass behavior.
- Do not overstate source support in docs.
- Do not silently change public config names or MQTT entity identity rules.

## Done Criteria

- Ticketmaster path publishes cheapest-price sensors for upcoming home games.
- Docker Compose deployment and `.env` configuration are documented clearly.
- Tests, lint, and type checks pass locally where tooling is available.
- README and docs reflect the real implementation and limitations.

## Review Checklist

- Is the source support claim accurate?
- Are config changes documented in `README.md` and `docs/OPERATIONS.md`?
- Are MQTT discovery IDs/topics stable?
- Are stale game entities cleaned up?
- Is failure handling explicit and non-destructive?

## Safety Rules

- Prefer official schedule and ticket APIs.
- If a provider is partial or unsupported, represent it honestly in code and docs.
- Never add instructions or code intended to bypass provider protections.
