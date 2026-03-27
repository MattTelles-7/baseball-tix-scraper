# Home Assistant

## Integration Model

The service publishes MQTT discovery topics so Home Assistant can create sensors automatically.

The app uses retained discovery payloads and retained state payloads. It also publishes a shared availability topic so Home Assistant can mark the entities unavailable if the service goes offline.

## Planned Entities

- One sensor per game per source for the cheapest price
- Provider health sensor per source
- Next poll sensor
- Last completed poll sensor
- Tracked home game count sensor

## Entity Behavior

- Discovery payloads are retained at `homeassistant/sensor/<unique_id>/config`.
- State payloads are retained on `mlb_ticket_tracker/.../state`.
- Attributes are published on `mlb_ticket_tracker/.../attributes` for game price sensors.
- Past-game entities are removed after the post-game grace window by publishing an empty retained discovery payload.

## Topic Examples

- Game price sensor unique ID: `mlb_tix_cincinnati_reds_824540_ticketmaster_lowest_price`
- Game price state topic: `mlb_ticket_tracker/games/824540/ticketmaster/state`
- Game price attributes topic: `mlb_ticket_tracker/games/824540/ticketmaster/attributes`
- Provider health topic: `mlb_ticket_tracker/providers/ticketmaster/health/state`
- Next poll topic: `mlb_ticket_tracker/service/next_poll/state`
- Tracked home games topic: `mlb_ticket_tracker/service/tracked_home_games/state`

## Attributes

- `game_datetime`
- `home_team`
- `away_team`
- `opponent`
- `venue`
- `source`
- `source_status`
- `source_url`
- `source_event_id`
- `currency`
- `price_is_all_in`
- `last_checked`
- `notes`

## Suggested Automations

- Notify when a Ticketmaster price drops below a threshold.
- Notify when a provider health sensor changes to `error` or `backoff`.
- Use the per-game sensors in a dashboard to graph price changes over time.

## Entity Naming

- Sensor names are human-readable, for example `Boston Red Sox at Cincinnati Reds Ticketmaster Price`.
- Unique IDs are deterministic and should not be edited manually.
