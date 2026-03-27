# Operations

## Deployment

Primary deployment target is Docker Compose on Debian 13.

## Runtime Files

- `.env`: user configuration
- `docker-compose.yml`: service definition
- `DATA_DIR/state.json`: local cache and dedupe state

## Common Tasks

- Deploy: `./scripts/deploy.sh`
- Follow logs: `./scripts/logs.sh`
- Rebuild/restart: `./scripts/update.sh`

## Troubleshooting

- Confirm MQTT credentials and broker reachability.
- Confirm `TICKETMASTER_API_KEY` is valid.
- Inspect container logs for provider errors and rate limiting.
