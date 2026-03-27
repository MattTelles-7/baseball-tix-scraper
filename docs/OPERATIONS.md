# Operations

## Deployment

Primary deployment target is Docker Compose on Debian 13.

After `.env` is filled in, deploy from the repo root with one command:

```bash
cp .env.example .env && ./scripts/deploy.sh
```

## Runtime Files

- `.env`: user configuration
- `docker-compose.yml`: service definition
- `DATA_DIR/state.json`: local cache and dedupe state

## Common Tasks

- Deploy: `./scripts/deploy.sh`
- Follow logs: `./scripts/logs.sh`
- Rebuild/restart: `./scripts/update.sh`
- Healthcheck: `docker compose exec mlb-ticket-tracker python -m mlb_ticket_tracker.cli healthcheck`

## Troubleshooting

- Confirm MQTT credentials and broker reachability.
- Confirm `TICKETMASTER_API_KEY` is valid.
- Inspect container logs for provider errors and rate limiting.
- If discovery entities are missing, confirm Home Assistant MQTT discovery is enabled and `MQTT_DISCOVERY_PREFIX` matches the broker setup.
- If prices are not updating, check whether Ticketmaster is returning event matches and whether the provider is in backoff after recent errors.
