# Home Assistant

## Integration Model

The service uses MQTT discovery. Home Assistant creates entities automatically from the retained discovery payloads.

The current entity model is intentionally small:

- one price sensor per `game x source`
- one provider health sensor per source
- three service sensors:
  - tracked home games
  - next poll
  - last completed poll

For a normal first deployment with this repo, that means:

- one or more `ticketmaster_lowest_price` sensors for upcoming home games
- one `ticketmaster_health` sensor
- three diagnostic service sensors

## Exact Entity Naming

### Price Sensors

Pattern:

- `sensor.<team_slug>_<game_pk>_<source>_lowest_price`

Actual current example:

- `sensor.cincinnati_reds_824540_ticketmaster_lowest_price`

Current discovery payload shape:

- discovery topic:
  `homeassistant/sensor/mlb_tix_cincinnati_reds_824540_ticketmaster_lowest_price/config`
- state topic:
  `mlb_ticket_tracker/games/824540/ticketmaster/state`
- attributes topic:
  `mlb_ticket_tracker/games/824540/ticketmaster/attributes`
- display name:
  `2026-03-28 vs Boston Red Sox Ticketmaster Price`

Price sensor attributes currently published by the repo:

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

### Provider Health Sensors

Pattern:

- `sensor.<team_slug>_<source>_health`

Actual current example:

- `sensor.cincinnati_reds_ticketmaster_health`

Current states:

- `healthy`
- `backoff`
- `error`
- `unconfigured`

Current provider health attributes:

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

Actual current examples:

- `sensor.cincinnati_reds_tracked_home_games`
- `sensor.cincinnati_reds_next_poll`
- `sensor.cincinnati_reds_last_completed_poll`

### Device Grouping

All discovered entities are grouped under one Home Assistant device per team.

Actual current example:

- device name: `Cincinnati Reds Ticket Tracker`
- device identifier: `mlb-ticket-tracker-cincinnati-reds`

## Dashboard YAML

These are ready-to-paste Lovelace YAML snippets using the repo's real entity naming scheme.

Replace the game-specific entity IDs with the actual discovered game sensors you care about. The naming pattern stays stable.

### Current Prices View

```yaml
title: Current Prices
path: current-prices
icon: mdi:ticket-confirmation-outline
cards:
  - type: entities
    title: Reds Current Ticket Prices
    show_header_toggle: false
    entities:
      - entity: sensor.cincinnati_reds_824540_ticketmaster_lowest_price
        name: 2026-03-28 vs Boston Red Sox
```

To track additional games in the same card, duplicate the `entity:` line with the other discovered `ticketmaster_lowest_price` sensors.

### History Graph View

```yaml
title: Price History
path: price-history
icon: mdi:chart-line
cards:
  - type: history-graph
    title: Reds Ticket Price History
    hours_to_show: 168
    refresh_interval: 300
    entities:
      - entity: sensor.cincinnati_reds_824540_ticketmaster_lowest_price
        name: 2026-03-28 vs Boston Red Sox
```

If you want to graph more than one game, add more discovered `ticketmaster_lowest_price` sensors to the `entities:` list.

### Diagnostics View

```yaml
title: Diagnostics
path: diagnostics
icon: mdi:stethoscope
cards:
  - type: entities
    title: Reds Ticket Tracker Diagnostics
    show_header_toggle: false
    entities:
      - entity: sensor.cincinnati_reds_ticketmaster_health
      - entity: sensor.cincinnati_reds_tracked_home_games
      - entity: sensor.cincinnati_reds_next_poll
      - entity: sensor.cincinnati_reds_last_completed_poll
```

## Package-Style Automation YAML

If you use Home Assistant packages, you can drop the block below into a package file such as:

- `config/packages/mlb_ticket_tracker.yaml`

If you do not use packages, copy the `input_number:` and `automation:` sections into the matching places in your Home Assistant config.

Replace:

- `notify.mobile_app_your_phone` with your real notify target
- `sensor.cincinnati_reds_824540_ticketmaster_lowest_price` with the actual game sensor you want to alert on

```yaml
input_number:
  reds_ticket_price_threshold:
    name: Reds Ticket Price Threshold
    min: 1
    max: 500
    step: 1
    unit_of_measurement: USD
    mode: box
    initial: 20

  reds_ticket_price_drop_threshold:
    name: Reds Ticket Price Drop Threshold
    min: 1
    max: 200
    step: 1
    unit_of_measurement: USD
    mode: box
    initial: 10

automation:
  - id: reds_ticketmaster_price_below_threshold
    alias: Reds Ticketmaster Price Below Threshold
    mode: single
    trigger:
      - platform: state
        entity_id: sensor.cincinnati_reds_824540_ticketmaster_lowest_price
    condition:
      - condition: template
        value_template: >
          {% set price = states(trigger.entity_id) %}
          {% set threshold = states('input_number.reds_ticket_price_threshold') %}
          {{ price not in ['unknown', 'unavailable', 'none', 'None']
             and threshold not in ['unknown', 'unavailable', 'none', 'None']
             and price | float <= threshold | float }}
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: Reds Ticket Alert
          message: >
            {{ state_attr(trigger.entity_id, 'matchup') }} is now
            ${{ states(trigger.entity_id) }} on
            {{ state_attr(trigger.entity_id, 'source_display_name') }}.

  - id: reds_ticketmaster_provider_unavailable
    alias: Reds Ticketmaster Provider Unavailable
    mode: restart
    trigger:
      - platform: state
        entity_id: sensor.cincinnati_reds_ticketmaster_health
        from: healthy
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state is not none
             and trigger.to_state.state in ['backoff', 'error', 'unconfigured'] }}
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: Reds Ticket Provider Issue
          message: >
            Ticketmaster health is now {{ states('sensor.cincinnati_reds_ticketmaster_health') }}.
            {% set last_error = state_attr('sensor.cincinnati_reds_ticketmaster_health', 'last_error') %}
            {% if last_error %}Last error: {{ last_error }}{% endif %}

  - id: reds_ticketmaster_large_price_drop
    alias: Reds Ticketmaster Large Price Drop
    mode: single
    trigger:
      - platform: state
        entity_id: sensor.cincinnati_reds_824540_ticketmaster_lowest_price
    condition:
      - condition: template
        value_template: >
          {% set old = trigger.from_state.state if trigger.from_state else none %}
          {% set new = trigger.to_state.state if trigger.to_state else none %}
          {% set drop_threshold = states('input_number.reds_ticket_price_drop_threshold') %}
          {{ old not in ['unknown', 'unavailable', 'none', 'None', none]
             and new not in ['unknown', 'unavailable', 'none', 'None', none]
             and drop_threshold not in ['unknown', 'unavailable', 'none', 'None']
             and (old | float - new | float) >= drop_threshold | float }}
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: Reds Ticket Price Dropped
          message: >
            {{ state_attr(trigger.entity_id, 'matchup') }} dropped from
            ${{ trigger.from_state.state }} to ${{ trigger.to_state.state }}
            on {{ state_attr(trigger.entity_id, 'source_display_name') }}.
```

## Practical Operator Notes

- Use the discovered `ticketmaster_lowest_price` sensors for all price alerts.
- Use `sensor.<team>_ticketmaster_health` for outage alerts instead of the raw MQTT availability topic.
- Keep your main dashboard limited to the few game sensors you actually care about.
- If a price sensor shows `unknown`, check the entity attributes, especially `notes`, before assuming the integration is broken.
- The entity IDs shown above are stable because the repo publishes deterministic `default_entity_id` values from the team slug, game PK, and source name.
