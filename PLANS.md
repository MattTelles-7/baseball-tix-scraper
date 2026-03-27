# PLANS.md

## Current Milestones

1. Bootstrap repo, tooling, docs, and deployment scripts.
2. Implement config, schedule, state, providers, and MQTT publishing.
3. Add tests, CI, Docker artifacts, and clear self-hosting docs.

## Current Assumptions

- Single-user deployment on Debian 13.
- Docker Compose is the primary install path.
- Ticketmaster public Discovery API is the first working source.
- SeatGeek and Vivid remain disabled by default in the initial release.

## Remaining Work

- Flesh out implementation modules under `src/`.
- Add provider integrations and Home Assistant publishing.
- Complete tests and smoke coverage.
- Finalize README quick start and troubleshooting guidance.
