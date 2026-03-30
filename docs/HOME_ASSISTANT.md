# Home Assistant

## Integration Model

The service uses MQTT discovery so Home Assistant creates entities automatically.

The entity model is intentionally small:

- one price sensor per `game x source`
- one provider status sensor per source
- three service sensors:
  - tracked home games
  - next poll
  - last completed poll

This keeps the integration stable enough for long-lived dashboards and automations without turning the repo into a custom Home Assistant integration.

## Design Choices

### Stable IDs

- `unique_id` values are deterministic and based on team slug, game PK, and source.
- `default_entity_id` values are also deterministic, so first-imported entity IDs are predictable.
- You can rename entities in Home Assistant later without breaking discovery because `unique_id` stays constant.

### Device Grouping

All entities are grouped under one Home Assistant device per team:

- device name: `Cincinnati Reds Ticket Tracker`
- device identifier: `mlb-ticket-tracker-cincinnati-reds`

This keeps the integration easy to find in the Devices view while avoiding one device per game.

### Price Sensor Shape

Price sensors are the primary entities for dashboards, history, and automations.

- They stay normal user-facing sensors.
- They use `suggested_display_precision: 2`.
- They keep stable, game-specific metadata as attributes.
- They do **not** include a poll-by-poll `last_checked` attribute because that would create unnecessary recorder churn and noisy state updates over time.

### Operational Sensors

Provider status and service sensors are marked as diagnostic entities so they stay available for troubleshooting and automations without cluttering the main UI.

## Entity Patterns

### Price Sensors

Pattern:

- discovery topic: `homeassistant/sensor/mlb_tix_<team>_<gamepk>_<source>_lowest_price/config`
- default entity ID: `sensor.<team>_<gamepk>_<source>_lowest_price`

Example:

- unique ID: `mlb_tix_cincinnati_reds_824540_ticketmaster_lowest_price`
- entity ID: `sensor.cincinnati_reds_824540_ticketmaster_lowest_price`
- state topic: `mlb_ticket_tracker/games/824540/ticketmaster/state`

Example display name:

- `2026-03-28 vs Boston Red Sox Ticketmaster Price`

Price sensor attributes:

- `game_id`
- `game_pk`
- `game_date`
- `game_datetime`
- `matchup`
- `home_team`
- `away_team`
- `opponent`
- `venue`
- `source`
- `source_display_name`
- `source_status`
- `source_url`
- `source_event_id`
- `currency`
- `price_is_all_in`
- `notes`

### Provider Status Sensors

Pattern:

- entity ID: `sensor.<team>_<source>_health`

Example:

- `sensor.cincinnati_reds_ticketmaster_health`

States:

- `healthy`
- `backoff`
- `error`
- `unconfigured`

These sensors use `device_class: enum` and are good automation triggers for outage or degradation alerts.

Provider status attributes:

- `source`
- `support_level`
- `auth_required`
- `implemented_fields`
- `limitations`
- `consecutive_failures`
- `last_successful_poll_at`
- `last_error_at`
- `last_error`
- `backoff_until`

### Service Sensors

Default entity IDs:

- `sensor.cincinnati_reds_tracked_home_games`
- `sensor.cincinnati_reds_next_poll`
- `sensor.cincinnati_reds_last_completed_poll`

These are diagnostic sensors and are mainly useful for troubleshooting, dashboards, and confirming the service is still polling.

## Availability Behavior

- All entities share the MQTT availability topic `mlb_ticket_tracker/availability`.
- If the service goes offline, Home Assistant marks the entities unavailable.
- Price discovery topics for past games are removed after the configured post-game grace window.

## Automation Examples

These examples use the default entity IDs. If you renamed entities in Home Assistant, substitute your final entity IDs.

### Notify When Ticket Price Drops Below Threshold

```yaml
alias: Reds ticket below threshold
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.cincinnati_reds_824540_ticketmaster_lowest_price
    below: 20
condition:
  - condition: template
    value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable'] }}"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: Cheap Reds ticket found
      message: >
        {{ state_attr(trigger.entity_id, 'matchup') }} is now
        ${{ trigger.to_state.state }} on
        {{ state_attr(trigger.entity_id, 'source_display_name') }}.
```

### Notify When A Provider Goes Down

```yaml
alias: Reds ticket provider outage
mode: restart
trigger:
  - platform: state
    entity_id: sensor.cincinnati_reds_ticketmaster_health
    from: healthy
condition:
  - condition: template
    value_template: "{{ trigger.to_state.state in ['backoff', 'error', 'unconfigured'] }}"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: Ticket provider issue
      message: >
        Ticketmaster status changed to {{ trigger.to_state.state }}.
        {% set last_error = state_attr(trigger.entity_id, 'last_error') %}
        {% if last_error %}Last error: {{ last_error }}{% endif %}
```

### Notify On Large Price Drop Since Last Publish

```yaml
alias: Reds ticket large price drop
mode: single
trigger:
  - platform: state
    entity_id: sensor.cincinnati_reds_824540_ticketmaster_lowest_price
condition:
  - condition: template
    value_template: >
      {% set old = trigger.from_state.state %}
      {% set new = trigger.to_state.state %}
      {{ old not in ['unknown', 'unavailable', None]
         and new not in ['unknown', 'unavailable', None]
         and (old | float - new | float) >= 10 }}
action:
  - service: notify.mobile_app_your_phone
    data:
      title: Reds ticket price dropped
      message: >
        {{ state_attr(trigger.entity_id, 'matchup') }} dropped
        from ${{ trigger.from_state.state }} to ${{ trigger.to_state.state }}
        on {{ state_attr(trigger.entity_id, 'source_display_name') }}.
```

## Dashboard Recommendations

### Recommended Layout

Use one dashboard view with three sections:

1. active game prices
2. price history
3. provider and service diagnostics

### Upcoming Price List Card

Good for quickly scanning current prices.

```yaml
type: entities
title: Reds Upcoming Ticket Prices
entities:
  - entity: sensor.cincinnati_reds_824540_ticketmaster_lowest_price
  - entity: sensor.cincinnati_reds_824541_ticketmaster_lowest_price
  - entity: sensor.cincinnati_reds_824542_ticketmaster_lowest_price
```

### Price History Graph

Useful for seeing drops over time on one or two target games.

```yaml
type: history-graph
title: Ticket Price History
hours_to_show: 168
refresh_interval: 300
entities:
  - entity: sensor.cincinnati_reds_824540_ticketmaster_lowest_price
  - entity: sensor.cincinnati_reds_824541_ticketmaster_lowest_price
```

### Diagnostics Card

Keep this in the same dashboard or a troubleshooting view.

```yaml
type: entities
title: Ticket Tracker Diagnostics
entities:
  - entity: sensor.cincinnati_reds_ticketmaster_health
  - entity: sensor.cincinnati_reds_tracked_home_games
  - entity: sensor.cincinnati_reds_next_poll
  - entity: sensor.cincinnati_reds_last_completed_poll
```

## Practical Recommendations

- Use the price sensors as the only notification triggers for ticket alerts.
- Use provider health sensors for outage notifications, not the raw MQTT availability state.
- Pin one or two especially important upcoming games to a history graph instead of graphing every game at once.
- Leave the operational sensors enabled, but keep them in a diagnostic card instead of your main price list.
- Build automations against entity IDs or areas you control in Home Assistant, not raw MQTT topics.
