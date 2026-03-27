# PLANS.md

## Current Milestones

1. Bootstrap repo, tooling, docs, and deployment scripts. Done.
2. Implement config, schedule, state, providers, and MQTT publishing. Done.
3. Add tests, CI, Docker artifacts, and clear self-hosting docs. Done.
4. Validate on a Debian 13 server with real MQTT and Ticketmaster credentials.

## Current Assumptions

- Single-user deployment on Debian 13.
- Docker Compose is the primary install path.
- Ticketmaster public Discovery API is the first working source.
- SeatGeek and Vivid remain disabled by default in the initial release.
- Home Assistant is already running MQTT or can be pointed at the same broker.

## Remaining Work

- Run a real broker/server smoke test on Debian 13.
- Confirm Ticketmaster auth and event matching on live data.
- Adjust README if the Debian server reveals any install friction.
