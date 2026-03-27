# Architecture

The service is a small polling application with five core parts:

1. Configuration loader
2. MLB schedule client and home-game filter
3. Provider adapters
4. JSON state/cache store
5. MQTT publisher for Home Assistant

## Flow

1. Load config from environment.
2. Fetch upcoming schedule for the configured team.
3. Filter to home games.
4. Match each game to provider events.
5. Fetch the cheapest price per matched event.
6. Publish MQTT discovery and state payloads.
7. Persist last-published state and cached provider metadata.

## Persistence

`DATA_DIR/state.json` stores dedupe state, cached event matches, provider health data, and cleanup metadata.

## Failure Handling

- A provider failure does not stop the full poll.
- Unsupported providers report capability and health honestly.
- Stale game entities are removed once they fall outside the retention window.
