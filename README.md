# MLB Home Ticket Tracker

Single-user service for tracking the cheapest current MLB home-game ticket price and publishing it into Home Assistant over MQTT discovery.

It is built for one person, one team, and one Debian 13 server. Ticketmaster Discovery API is the working source in this branch. SeatGeek and Vivid are present as disabled scaffolds only.

## Quick Start

1. Copy the example env file: `cp .env.example .env`
2. Edit `.env` with your team, MQTT broker, and Ticketmaster key.
3. Validate the config without contacting Ticketmaster or MQTT: `./scripts/validate.sh`
4. Set `DRY_RUN=true` in `.env` for the first startup.
5. Start it with one command: `./scripts/deploy.sh`
6. Check `./scripts/health.sh` and `./scripts/logs.sh`
7. Set `DRY_RUN=false` in `.env` and run `./scripts/update.sh`

If you change config later, rerun `./scripts/update.sh`. To watch logs, run `./scripts/logs.sh`.

## What It Publishes

- One sensor per game per source for the cheapest current price
- Provider health sensors
- Next poll time
- Tracked home game count

## Configuration

Put everything in the root `.env` file.

### Ticketmaster-Only Variables You Must Set

For the first real deployment, set exactly these values:

| Variable | Required for first run | Notes |
| --- | --- | --- |
| `TEAM_ID` | Yes | Easiest team selector. Use `TEAM_SLUG` or `TEAM_NAME` only if you prefer not to use the numeric ID. |
| `TICKETMASTER_API_KEY` | Yes | Public Ticketmaster Discovery API key. |
| `MQTT_HOST` | Yes | Hostname or IP of the broker Home Assistant uses. |
| `MQTT_PORT` | Yes | Usually `1883`. |
| `MQTT_USERNAME` | If broker uses auth | Leave empty only if your broker allows anonymous access. |
| `MQTT_PASSWORD` | If broker uses auth | Leave empty only if your broker allows anonymous access. |
| `TIMEZONE` | If default is wrong | Keep `America/New_York` unless your server/team handling should use another IANA timezone. |
| `POLL_INTERVAL_MINUTES` | If default is wrong | Keep `15` unless you want a slower or faster poll cadence. |
| `DATA_DIR` | If default is wrong | Keep `./data` unless you want state stored somewhere else. |

Keep these as-is for a first Ticketmaster-only deployment:

```env
ENABLE_TICKETMASTER=true
ENABLE_SEATGEEK=false
ENABLE_VIVID=false
ENABLE_EXPERIMENTAL_ADAPTERS=false
HOME_GAMES_ONLY=true
```

### Required values

| Variable | Purpose | Example |
| --- | --- | --- |
| `TEAM_ID` | MLB team ID to track | `113` |
| `TICKETMASTER_API_KEY` | Ticketmaster Discovery API key | `replace_me` |
| `MQTT_HOST` | MQTT broker host | `homeassistant.local` |
| `MQTT_PORT` | MQTT broker port | `1883` |
| `MQTT_USERNAME` | MQTT username if your broker uses auth | `replace_me` |
| `MQTT_PASSWORD` | MQTT password if your broker uses auth | `replace_me` |

### Common values

| Variable | Purpose | Default |
| --- | --- | --- |
| `HOME_GAMES_ONLY` | Track only home games | `true` |
| `LOOKAHEAD_DAYS` | Look ahead this many days | `60` |
| `POLL_INTERVAL_MINUTES` | How often to poll | `15` |
| `MATCH_CACHE_TTL_HOURS` | How long to keep cached provider event matches before re-matching | `24` |
| `TIMEZONE` | Local timezone for game handling | `America/New_York` |
| `DATA_DIR` | Host directory for local state when using Docker Compose | `./data` |
| `POST_GAME_GRACE_MINUTES` | Keep recent games around before cleanup | `240` |
| `FAILURE_RETRY_SECONDS` | Retry delay after MQTT or service-level failures | `30` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DRY_RUN` | Log publishes without sending MQTT messages | `false` |

### Provider toggles

| Variable | Purpose | Default |
| --- | --- | --- |
| `ENABLE_TICKETMASTER` | Enable Ticketmaster polling | `true` |
| `ENABLE_SEATGEEK` | Enable the SeatGeek scaffold | `false` |
| `ENABLE_VIVID` | Enable the Vivid scaffold | `false` |
| `ENABLE_EXPERIMENTAL_ADAPTERS` | Allow experimental adapters to load | `false` |

### MQTT values

| Variable | Purpose | Default |
| --- | --- | --- |
| `MQTT_TOPIC_PREFIX` | State topic prefix | `mlb_ticket_tracker` |
| `MQTT_DISCOVERY_PREFIX` | Home Assistant discovery prefix | `homeassistant` |
| `MQTT_CLIENT_ID` | MQTT client ID | `mlb-ticket-tracker` |
| `MQTT_KEEPALIVE` | MQTT keepalive seconds | `60` |

### Rate limit and timeout values

| Variable | Purpose | Default |
| --- | --- | --- |
| `HTTP_TIMEOUT_SECONDS` | HTTP request timeout | `20` |
| `REQUEST_JITTER_SECONDS` | Random delay added between polls | `5` |
| `TICKETMASTER_RATE_LIMIT_DELAY_SECONDS` | Delay after Ticketmaster requests | `0.5` |
| `SEATGEEK_RATE_LIMIT_DELAY_SECONDS` | Delay after SeatGeek requests | `0.5` |
| `VIVID_RATE_LIMIT_DELAY_SECONDS` | Delay after Vivid requests | `1.0` |

## Reds Example

For Cincinnati Reds, set:

```env
TEAM_ID=113
TIMEZONE=America/New_York
HOME_GAMES_ONLY=true
ENABLE_TICKETMASTER=true
ENABLE_SEATGEEK=false
ENABLE_VIVID=false
```

## First-Run Checklist

- Ticketmaster API key:
  Use a real Discovery API key in `TICKETMASTER_API_KEY`.
- MQTT broker settings:
  Set `MQTT_HOST`, `MQTT_PORT`, and broker auth if required.
- MLB team selection:
  Set `TEAM_ID=113` for the Reds, or replace it with your team’s MLB ID.
- Timezone:
  Keep `TIMEZONE=America/New_York` unless you need another IANA timezone.
- Poll interval:
  Keep `POLL_INTERVAL_MINUTES=15` unless you want a different cadence.
- Data directory:
  Keep `DATA_DIR=./data` unless you want the state file elsewhere.

## Safe First Run

1. Copy and edit the env file:

```bash
cp .env.example .env
```

2. Validate config without publishing anything:

```bash
./scripts/validate.sh
```

Expected output:

- JSON with `"ok": true`
- your resolved team under `"details.team"`
- `"data_dir_status": "writable"`
- `"providers.ticketmaster.enabled": true`

3. Force the first container start into dry-run mode:

```bash
sed -i 's/^DRY_RUN=false$/DRY_RUN=true/' .env
./scripts/deploy.sh
./scripts/health.sh
./scripts/logs.sh
```

Expected output:

- `./scripts/health.sh` returns JSON with `status` changing from `starting` to `ok` after the first poll cycle
- logs include `service_started`, `poll_cycle_started`, `mqtt_dry_run_mode`, and `dry_run_publish_entity`

4. Turn on real MQTT publishing:

```bash
sed -i 's/^DRY_RUN=true$/DRY_RUN=false/' .env
./scripts/update.sh
./scripts/health.sh
```

Expected output:

- healthcheck returns JSON with `"ok": true`
- Home Assistant starts discovering price and health sensors

## Home Assistant

Enable MQTT in Home Assistant, point it at the same broker, and keep the discovery prefix aligned with `MQTT_DISCOVERY_PREFIX`.

The app creates stable MQTT discovery entities for each `game x source` price sensor, plus provider health and service sensors. Discovery payloads are retained, and stale game entities are removed after they fall outside the post-game grace window.

See `docs/HOME_ASSISTANT.md` for the exact topic names and sample automations.
See `docs/HANDOFF.md` for the operator handoff, day-2 procedures, and roadmap.

## Support Matrix

- Ticketmaster: supported
- SeatGeek: scaffold only
- Vivid Seats: scaffold only, unsupported by default

## Limitations

- No SQL backend in v1
- No anti-bot or bypass behavior
- No MLB Ballpark integration
- Ticketmaster publishes `priceRanges.min` from the public Discovery API, which is a best-effort cheapest-price signal, not guaranteed live listing parity

## Testing

Run the local checks with:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src tests
```

## Runtime Files

- `.env`: your config
- `data/state.json`: lightweight local state
- `docker-compose.yml`: service definition
- `scripts/deploy.sh`: start/rebuild the service
- `scripts/update.sh`: rebuild after changes
- `scripts/validate.sh`: validate config in Docker without publishing
- `scripts/logs.sh`: follow container logs
- `scripts/health.sh`: run the built-in JSON healthcheck

## Maintainability Notes

- The service orchestration is split into schedule fetch, provider execution, publish, and runtime-update helpers so provider work can be tested in isolation.
- Provider event matches are cached in `state.json`, but they expire after `MATCH_CACHE_TTL_HOURS` so stale fuzzy matches do not live forever.
