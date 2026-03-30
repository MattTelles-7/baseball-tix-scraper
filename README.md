# MLB Home Ticket Tracker

Single-user service for tracking the cheapest current MLB home-game ticket price and publishing it into Home Assistant over MQTT discovery.

It is built for one person, one team, and one Debian 13 server. Ticketmaster Discovery API is the working source in this branch. SeatGeek and Vivid are present as disabled scaffolds only.

## Quick Start

1. Copy the example env file: `cp .env.example .env`
2. Edit `.env` with your team, MQTT broker, and Ticketmaster key.
3. Start it with one command: `./scripts/deploy.sh`

If you change config later, rerun `./scripts/update.sh`. To watch logs, run `./scripts/logs.sh`.

## What It Publishes

- One sensor per game per source for the cheapest current price
- Provider health sensors
- Next poll time
- Tracked home game count

## Configuration

Put everything in the root `.env` file.

### Required values

| Variable | Purpose | Example |
| --- | --- | --- |
| `TEAM_ID` | MLB team ID to track | `113` |
| `TICKETMASTER_API_KEY` | Ticketmaster Discovery API key | `replace_me` |
| `MQTT_HOST` | MQTT broker host | `homeassistant.local` |
| `MQTT_PORT` | MQTT broker port | `1883` |
| `MQTT_USERNAME` | MQTT username | `replace_me` |
| `MQTT_PASSWORD` | MQTT password | `replace_me` |

### Common values

| Variable | Purpose | Default |
| --- | --- | --- |
| `HOME_GAMES_ONLY` | Track only home games | `true` |
| `LOOKAHEAD_DAYS` | Look ahead this many days | `60` |
| `POLL_INTERVAL_MINUTES` | How often to poll | `15` |
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

## Home Assistant

Enable MQTT in Home Assistant, point it at the same broker, and keep the discovery prefix aligned with `MQTT_DISCOVERY_PREFIX`.

The app creates stable MQTT discovery entities for each `game x source` price sensor, plus provider health and service sensors. Discovery payloads are retained, and stale game entities are removed after they fall outside the post-game grace window.

See `docs/HOME_ASSISTANT.md` for the exact topic names and sample automations.

## Support Matrix

- Ticketmaster: supported
- SeatGeek: partial scaffold only
- Vivid Seats: unsupported-by-default scaffold only

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
- `scripts/logs.sh`: follow container logs
- `scripts/health.sh`: run the built-in JSON healthcheck
