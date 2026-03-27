# Home Assistant

## Integration Model

The service publishes MQTT discovery topics so Home Assistant can create sensors automatically.

## Planned Entities

- One sensor per game per source for the cheapest price
- Provider health sensor
- Next poll sensor
- Tracked home game count sensor

## Entity Behavior

- Discovery payloads are retained.
- State payloads are retained.
- Past-game entities are removed after a grace period by publishing empty retained config payloads.

## Attributes

- game datetime
- opponent
- venue
- source name
- source URL
- source event ID
- support level
- last checked time
- notes or caveats
