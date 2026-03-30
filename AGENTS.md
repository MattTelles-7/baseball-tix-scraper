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

Current branch state: the service already has the core schedule, state, Ticketmaster, and MQTT publishing code. Treat the docs as release docs for a working single-user service, not a blank bootstrap.

## Commands

- Create venv: `python3 -m venv .venv`
- Install dev deps: `.venv/bin/pip install -e .[dev]`
- Run tests: `.venv/bin/pytest`
- Lint: `.venv/bin/ruff check .`
- Format check: `.venv/bin/ruff format --check .`
- Type check: `.venv/bin/mypy src tests`
- Deploy locally: `./scripts/deploy.sh`
- Update/restart locally: `./scripts/update.sh`
- Tail logs: `./scripts/logs.sh`

## Conventions

- Python 3.12+.
- Keep modules small and typed.
- Prefer official/public APIs over scraping.
- Keep Home Assistant entity IDs and MQTT topics deterministic.
- Persist only lightweight JSON state in `DATA_DIR`.
- Update docs with code changes.
- Keep README simple and operational for a single Debian 13 user.

## Do-Not Rules

- Do not add SQL as a v1 dependency.
- Do not add anti-bot evasion, CAPTCHA handling, proxy rotation, or Cloudflare bypass behavior.
- Do not add browser automation, login automation, or account-session reuse for ticket sources unless the repo docs and decisions are explicitly updated first.
- Do not overstate source support in docs.
- Do not silently change public config names or MQTT entity identity rules.
- Do not log or persist raw credential-bearing error strings; redact API keys, tokens, passwords, and secrets before writing logs, MQTT attributes, health output, or `state.json`.

## Done Criteria

- Ticketmaster path publishes cheapest-price sensors for upcoming home games.
- Docker Compose deployment and `.env` configuration are documented clearly.
- Tests, lint, and type checks pass locally where tooling is available.
- README and docs reflect the real implementation and limitations.
- SeatGeek and Vivid are described honestly as partial or unsupported-by-default scaffolds.

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
- If a provider would require anti-bot work, a browser session, or customer-account automation to function, stop and document it as unsupported instead of implementing a workaround.
- Treat `state.json`, healthcheck output, and provider health attributes as operator-visible surfaces and keep them free of secrets.
