# Operator Handoff

## What This Service Supports Today

### Supported

- MLB schedule lookup through the public MLB stats API
- Upcoming home-game filtering for one configured MLB team
- Ticketmaster polling through the public Discovery API
- Publishing one Home Assistant MQTT discovery price sensor per upcoming home game for Ticketmaster
- Publishing Home Assistant provider health and service status sensors
- Lightweight local JSON state in `DATA_DIR/state.json`
- Docker Compose deployment on a single self-hosted server

### Partial

- No live partial provider is enabled today
- SeatGeek is only a scaffold in this release, but it is the most realistic future partial provider

### Intentionally Unsupported

- Vivid as a real buyer-facing integration
- MLB Ballpark integration
- SQL storage
- Browser automation
- Account-session reuse
- Anti-bot evasion
- CAPTCHA handling
- Proxy rotation
- Cloudflare bypass

## Architecture In Plain English

This service is a small long-running poller.

It wakes up on a schedule, asks MLB for the upcoming home games for your team, tries to match those games to Ticketmaster events, reads the public minimum ticket price from Ticketmaster, and publishes the result into Home Assistant through MQTT discovery.

It keeps only a small local state file so it can remember what it already published, retain provider health history, and avoid rebuilding everything from scratch after every restart. Home Assistant is the real place where history, dashboards, and automations live.

If Ticketmaster fails temporarily, the service does not crash permanently. It records the failure, backs off, and keeps trying again on later poll cycles.

## Startup Steps

1. Check out the release branch or tag you want to run.
2. Copy `.env.example` to `.env`.
3. Fill in your real values for:
   `TEAM_ID`, `TICKETMASTER_API_KEY`, `MQTT_HOST`, `MQTT_PORT`, and broker auth if required.
4. Run `./scripts/validate.sh`.
5. For the very first launch, set `DRY_RUN=true` in `.env`.
6. Run `./scripts/deploy.sh`.
7. Run `docker compose ps`, `./scripts/health.sh`, and `./scripts/logs.sh`.
8. When the dry run looks correct, set `DRY_RUN=false` and run `./scripts/update.sh`.
9. Verify Home Assistant discovered the device and sensors.

## Upgrade Steps

1. Pull the new branch, tag, or commit.
2. Review `.env.example` for any new variables.
3. Update `.env` if needed.
4. Run `./scripts/validate.sh`.
5. Run `./scripts/update.sh`.
6. Verify with:
   `docker compose ps`
   `./scripts/health.sh`
   `./scripts/logs.sh`
7. Confirm Home Assistant still shows the expected Ticketmaster and service sensors.

## Rollback Steps

1. Identify the last known good branch, tag, or commit.
2. Check it out locally.
3. If the new version changed `.env`, restore the last known good `.env`.
4. If you took a backup before upgrade, restore `DATA_DIR/state.json` too.
5. Run `./scripts/update.sh`.
6. Verify health and logs again.

For a simple rollback after tagging, the practical flow is:

```bash
git checkout <last-known-good-tag-or-commit>
./scripts/update.sh
./scripts/health.sh
./scripts/logs.sh
```

## Backup And Restore Steps

### Back Up

- `.env`
- `DATA_DIR/state.json`

Simple example:

```bash
tar -czf mlb-ticket-tracker-backup.tgz .env data/state.json
```

### Restore

1. Restore `.env`
2. Restore `DATA_DIR/state.json`
3. Run `./scripts/deploy.sh`
4. Verify with `./scripts/health.sh`

## Routine Maintenance Steps

- Check `./scripts/health.sh` periodically.
- Check `./scripts/logs.sh` after any config change or restart.
- Keep an eye on `sensor.<team>_ticketmaster_health` in Home Assistant.
- Review `.env.example` before upgrades.
- Keep Docker and the host OS patched.
- Take a backup before upgrades.
- Occasionally verify that Home Assistant is still receiving MQTT discovery updates and that at least one price sensor is alive for an upcoming game.

## What Logs To Check First

Start with `./scripts/logs.sh`.

The first log events to care about are:

- `service_started`
- `mqtt_connected`
- `poll_cycle_started`
- `provider_matches_refreshed`
- `poll_cycle_completed`

The first failure events to care about are:

- `mqtt_connect_failed`
- `mqtt_publish_failed`
- `provider_cycle_failed`
- `provider_in_backoff`
- `provider_unconfigured`
- `service_iteration_failed`

## What Not To Change Casually

- `MQTT_TOPIC_PREFIX`
- `MQTT_DISCOVERY_PREFIX`
- team selection variables once Home Assistant has already created entities
- the Home Assistant entity naming assumptions in the docs
- `DATA_DIR` without moving `state.json`
- provider toggles for SeatGeek or Vivid on a production instance
- `MATCH_CACHE_TTL_HOURS` unless you are fixing an event-matching problem
- `POLL_INTERVAL_MINUTES` to something aggressively low without a clear reason

Changing those can create new entities, strand old discovery entities, invalidate assumptions in dashboards and automations, or make troubleshooting harder.

## First Week Of Operation Checklist

- Day 1:
  confirm first dry run, first real publish, and Home Assistant discovery
- Day 1:
  verify `sensor.<team>_ticketmaster_health` settles on `healthy`
- Day 1:
  confirm at least one upcoming-game Ticketmaster price sensor exists
- Day 2:
  confirm `last_completed_poll` keeps advancing
- Day 2:
  confirm `next_poll` always stays in the future
- Day 3:
  inspect logs for repeated Ticketmaster failures or MQTT reconnect issues
- Day 3:
  confirm a restart with `docker compose restart mlb-ticket-tracker` recovers cleanly
- Day 5:
  verify your Home Assistant alert automation fires correctly with a test threshold
- Day 7:
  take a fresh backup of `.env` and `state.json`

## Future Roadmap

### Safe Next Steps

- implement real SeatGeek partial support through its official API
- improve docs around team IDs and example Home Assistant packages
- tighten CI and release/tag workflow
- add a small operator status summary command if it stays read-only and local
- add more tests around provider failure and match-quality edge cases

### Risky Or Brittle Next Steps

- anything that depends on browser automation
- anything that depends on customer-account login reuse
- anything that depends on undocumented buyer-site endpoints
- anything that requires anti-bot evasion or traffic shaping tricks
- adding Vivid support without a clean official buyer-facing API path
- broadening scope into multi-user or SQL-backed history before the single-user service is fully stable
