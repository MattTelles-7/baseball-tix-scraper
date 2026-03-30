# Operations

## Deployment

Target platform is Docker Compose on Debian 13.

### Prerequisites

- Docker Engine with the Compose plugin installed
- A writable host directory for `DATA_DIR`
- A reachable MQTT broker
- A valid `TICKETMASTER_API_KEY`

### First Deploy

1. Copy the example env file:

```bash
cp .env.example .env
```

2. Edit `.env` and set the Ticketmaster, team, MQTT, timezone, poll interval, and data directory values you want.
3. Validate the config in Docker without contacting Ticketmaster or publishing MQTT:

```bash
./scripts/validate.sh
```

Expected output:

- JSON with `"ok": true`
- resolved team details
- `"data_dir_status": "writable"`
- Ticketmaster enabled and configured

4. Set `DRY_RUN=true` in `.env` for the first service start.
5. Start or rebuild the service:

```bash
./scripts/deploy.sh
```

6. Verify container health:

```bash
docker compose ps
./scripts/health.sh
```

7. Confirm logs look sane:

```bash
./scripts/logs.sh
```

Expected early log events:

- `service_started`
- `poll_cycle_started`
- `mqtt_dry_run_mode`
- `dry_run_publish_entity`

8. After the dry run looks correct, set `DRY_RUN=false` in `.env` and restart:

```bash
./scripts/update.sh
```

### First Deployment Verification Checklist

Use this once `DRY_RUN=false` is set and the real publishing run has started.

1. Verify the container boots and stays up:

```bash
docker compose ps
```

Expected result:

- `mlb-ticket-tracker` shows `Up`
- health status transitions to `healthy` after the first completed poll

2. Verify the healthcheck output is sane:

```bash
./scripts/health.sh
```

Expected result:

- JSON with `"ok": true`
- `"status": "ok"`
- a recent `last_heartbeat_at`
- a non-null `next_poll_at`

3. Verify MQTT connection succeeds:

```bash
./scripts/logs.sh
```

Expected log signal:

- `mqtt_connected`

If you still have `DRY_RUN=true`, expect `mqtt_dry_run_mode` instead.

4. Verify Ticketmaster polling completes cleanly:

```bash
./scripts/logs.sh
```

Expected log signals:

- `poll_cycle_started`
- `provider_matches_refreshed` with `source` set to `ticketmaster`
- `poll_cycle_completed`

Things you should **not** see in a healthy first pass:

- `provider_cycle_failed` for `ticketmaster`
- `provider_in_backoff` for `ticketmaster`
- `mqtt_connect_failed`
- `mqtt_publish_failed`

5. Verify Home Assistant MQTT discovery creates the device and entities:

In Home Assistant:

- confirm the MQTT integration is connected to the same broker
- open Devices and look for `<Team Name> Ticket Tracker`
- confirm the device contains service sensors and the Ticketmaster health sensor

6. Verify the first Ticketmaster price sensor exists:

In Home Assistant Entities:

- find an entity like `sensor.<team>_<gamepk>_ticketmaster_lowest_price`

Expected result:

- the entity exists for at least one upcoming home game
- the state is numeric if Ticketmaster exposes a public price range
- if the state is `unknown`, inspect the sensor attributes and `notes` for event-match or public-price-range limitations

7. Verify provider and service status entities:

Expected entities:

- `sensor.<team>_ticketmaster_health`
- `sensor.<team>_tracked_home_games`
- `sensor.<team>_next_poll`
- `sensor.<team>_last_completed_poll`

Expected first-run states:

- Ticketmaster health should settle on `healthy`
- tracked home games should be greater than or equal to `0`
- next poll should be a future timestamp
- last completed poll should be a recent timestamp

8. Verify restart behavior once:

```bash
docker compose restart mlb-ticket-tracker
docker compose ps
./scripts/health.sh
```

Expected result:

- the container comes back without manual cleanup
- health returns to `ok` after the next poll cycle
- previously discovered entities remain stable in Home Assistant

## Runtime Files

- `.env`: user configuration
- `docker-compose.yml`: service definition with restart and healthcheck settings
- `DATA_DIR/state.json`: local cache and dedupe state
- Docker container logs: `docker compose logs mlb-ticket-tracker`

## Common Tasks

- Deploy: `./scripts/deploy.sh`
- Follow logs: `./scripts/logs.sh`
- Rebuild/restart: `./scripts/update.sh`
- Validate config: `./scripts/validate.sh`
- Healthcheck: `./scripts/health.sh`
- Inspect container status: `docker compose ps`
- Stop the service: `docker compose down`

## Health And Recovery

- The container uses Docker restart policy `unless-stopped`.
- Docker health checks call `mlb-ticket-tracker healthcheck --json`.
- Health is based on the persisted runtime heartbeat, not external source success.
- Source failures do not stop the process. Providers back off independently and the service keeps running.
- MQTT and other service-level failures trigger a short retry loop controlled by `FAILURE_RETRY_SECONDS`.
- Recent runtime failures are recorded in `state.json` and surfaced by the healthcheck output.
- Cached provider event matches are re-used for resilience but are expired after `MATCH_CACHE_TTL_HOURS`.

## Known Good First-Run Signals

During a healthy first real run, you should see most or all of these:

- `docker compose ps` shows the container as `Up` and then `healthy`
- `./scripts/health.sh` returns JSON with `"ok": true` and `"status": "ok"`
- logs show `service_started`, `mqtt_connected`, `poll_cycle_started`, `provider_matches_refreshed`, and `poll_cycle_completed`
- Home Assistant creates one device for your tracked team
- Home Assistant shows `sensor.<team>_ticketmaster_health` with state `healthy`
- Home Assistant shows service sensors for tracked game count, next poll, and last completed poll
- Home Assistant shows at least one `ticketmaster_lowest_price` entity for an upcoming home game

If the price sensor exists but reads `unknown`, that can still be a partially successful first run. Check the entity attributes and logs to see whether Ticketmaster lacked a public price range or the game did not match cleanly.

## Upgrade

1. Pull or update the repo.
2. Review any changes to `.env.example`.
3. Update `.env` if new variables were added.
4. Rebuild and restart:

```bash
./scripts/update.sh
```

5. Confirm healthy startup with:

```bash
docker compose ps
./scripts/health.sh
```

## Backup And Restore

### What To Back Up

- `.env`
- `DATA_DIR/state.json`

### Simple Backup Example

```bash
tar -czf mlb-ticket-tracker-backup.tgz .env data/state.json
```

### Restore

1. Restore `.env`
2. Restore `DATA_DIR/state.json`
3. Run `./scripts/deploy.sh`

The service can recreate discovery payloads and provider matches over time, but keeping `state.json` preserves dedupe history and provider health metadata across restarts.

## Troubleshooting

- Confirm MQTT credentials and broker reachability.
- Confirm `TICKETMASTER_API_KEY` is valid.
- Run `./scripts/health.sh` and inspect `last_error`, `last_completed_poll_at`, and provider health details.
- Inspect container logs for provider errors, MQTT connection failures, and rate limiting.
- If discovery entities are missing, confirm Home Assistant MQTT discovery is enabled and `MQTT_DISCOVERY_PREFIX` matches the broker setup.
- If prices are not updating, check whether Ticketmaster is returning event matches and whether the provider is in backoff after recent errors.
- If a provider starts tracking the wrong event, lower `MATCH_CACHE_TTL_HOURS` temporarily or remove the stale entry from `DATA_DIR/state.json` and restart the service.
- If the container is restarting repeatedly, run `docker compose logs mlb-ticket-tracker` and check for configuration errors or an unreachable MQTT broker.
- If you need to force a clean rebuild after image changes, run `docker compose down` followed by `./scripts/deploy.sh`.

## First 15 Minutes Troubleshooting

If the first launch does not look right, work through these in order:

1. Container never becomes healthy:
   Run `docker compose ps`, then `./scripts/health.sh`, then `./scripts/logs.sh`.
   Look for config errors, timezone validation failures, or a missing/wrong `DATA_DIR`.

2. MQTT never connects:
   Look for `mqtt_connect_failed` or `mqtt_publish_failed`.
   Re-check `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, and that Home Assistant points at the same broker.

3. Ticketmaster fails or backs off:
   Look for `provider_cycle_failed` or `provider_in_backoff` with `source=ticketmaster`.
   Re-check `TICKETMASTER_API_KEY`, outbound network access, and whether the provider is returning HTTP errors or rate limits.

4. Home Assistant does not create entities:
   Confirm MQTT discovery is enabled in Home Assistant and that `MQTT_DISCOVERY_PREFIX` matches on both sides.
   Confirm the Home Assistant MQTT integration is connected to the same broker the service uses.

5. Provider health entity exists but price sensors do not:
   Check upcoming home games for the configured team.
   Check logs for Ticketmaster matching issues.
   Remember that some games may not expose a public `priceRanges.min`, which results in `unknown` state rather than a numeric price.
