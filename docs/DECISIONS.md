# Decisions

## 2026-03-27: Docker Compose As The Primary Install Path

- Decision: ship Docker Compose plus a single `.env` file as the primary deployment workflow.
- Rationale: simplest path for a single self-hosting user on Debian 13.
- Consequence: Docker artifacts and docs are first-class deliverables.

## 2026-03-27: Ticketmaster Discovery API As The First Working Source

- Decision: implement Ticketmaster using the public Discovery API in the first release.
- Rationale: official documented access without requiring privileged marketplace credentials.
- Consequence: the published price signal must be documented as a public minimum price estimate, not guaranteed live listing parity.

## 2026-03-27: JSON State Instead Of SQL

- Decision: persist only lightweight JSON state in v1.
- Rationale: simpler deployment and sufficient for dedupe, event caching, and cleanup.
- Consequence: no built-in historical database beyond Home Assistant history.

## 2026-03-27: Discovery Price Signal Is Ticketmaster `priceRanges.min`

- Decision: publish Ticketmaster Discovery `priceRanges.min` as the working cheapest-price signal.
- Rationale: it is the best honest public signal available without privileged access.
- Consequence: docs must state that it is a best-effort price estimate, not guaranteed live listing parity.

## 2026-03-27: SeatGeek And Vivid Stay Scaffolded

- Decision: keep SeatGeek and Vivid disabled by default and explicitly labeled as partial or unsupported.
- Rationale: the branch should not overstate source support or depend on brittle undocumented behavior.
- Consequence: future work can add those providers without pretending they are ready today.

## 2026-03-27: Home Assistant Entity Cleanup After Grace Window

- Decision: remove stale game entities after a post-game grace period.
- Rationale: keeps Home Assistant tidy while preserving useful history in HA itself.
- Consequence: entity state history remains in Home Assistant, but old MQTT discovery entities do not accumulate.
