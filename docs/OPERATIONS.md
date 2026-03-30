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

2. Edit `.env` and set the required values.
3. Start or rebuild the service:

```bash
./scripts/deploy.sh
```

4. Verify container health:

```bash
docker compose ps
./scripts/health.sh
```

## Runtime Files

- `.env`: user configuration
- `docker-compose.yml`: service definition with restart and healthcheck settings
- `DATA_DIR/state.json`: local cache and dedupe state
- Docker container logs: `docker compose logs mlb-ticket-tracker`

## Common Tasks

- Deploy: `./scripts/deploy.sh`
- Follow logs: `./scripts/logs.sh`
- Rebuild/restart: `./scripts/update.sh`
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
