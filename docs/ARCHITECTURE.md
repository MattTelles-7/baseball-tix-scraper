# Architecture

The service is a small polling application with five core parts:

1. Configuration loader
2. MLB schedule client and home-game filter
3. Provider adapters
4. JSON state/cache store
5. MQTT publisher for Home Assistant

## Flow

1. Load config from environment.
2. Resolve the configured MLB team.
3. Fetch upcoming schedule data from the public MLB stats API.
4. Filter to home games and keep recent games within the post-game grace window.
5. Match each game to provider events.
6. Fetch the cheapest current price per matched event.
7. Publish MQTT discovery, state, and attributes.
8. Persist last-published state and cached provider metadata in JSON.

## Persistence

`DATA_DIR/state.json` stores dedupe state, cached event matches, provider health data, and cleanup metadata.

The file is updated atomically and is intentionally lightweight. There is no SQL database in this branch.

## MQTT Model

- Discovery topic: `homeassistant/sensor/<unique_id>/config`
- Game price state topic: `mlb_ticket_tracker/games/<gamePk>/<source>/state`
- Game price attributes topic: `mlb_ticket_tracker/games/<gamePk>/<source>/attributes`
- Shared availability topic: `mlb_ticket_tracker/availability`
- Device grouping: one device per tracked team

Entity IDs are deterministic and derived from team slug, game PK, and source name. The service also publishes `tracked_home_games`, `next_poll`, and `last_completed_poll` sensors.

## Failure Handling

- A provider failure does not stop the full poll.
- Unsupported providers report capability and health honestly.
- Stale game entities are removed once they fall outside the retention window.
- If a source is disabled or unconfigured, the service keeps running and publishes that status instead of failing hard.
