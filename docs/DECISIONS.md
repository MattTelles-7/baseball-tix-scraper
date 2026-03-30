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

## 2026-03-30: SeatGeek Moves To Partial Official-API Support

- Decision: move SeatGeek from scaffold-only to partial support through the official Platform API, while keeping it disabled by default.
- Rationale: the official API exposes event performer roles and `stats.lowest_price`, which is enough for an honest lowest-price signal without browser automation.
- Consequence: SeatGeek can now be enabled with `SEATGEEK_CLIENT_ID`, but docs must still warn that prices may remain unknown when the public API omits a lowest price and that all-in pricing is not exposed.

## 2026-03-30: Vivid Remains Scaffold-Only

- Decision: keep Vivid disabled by default and explicitly labeled unsupported beyond scaffold hooks.
- Rationale: the visible official API surface remains broker-oriented and is not a clean buyer-facing fit for this service.
- Consequence: the repo continues to avoid brittle or evasive Vivid integrations.

## 2026-03-27: Home Assistant Entity Cleanup After Grace Window

- Decision: remove stale game entities after a post-game grace period.
- Rationale: keeps Home Assistant tidy while preserving useful history in HA itself.
- Consequence: entity state history remains in Home Assistant, but old MQTT discovery entities do not accumulate.

## 2026-03-29: Security Posture Is Public-API-Only And Secret-Aware

- Decision: keep the repo limited to official or clearly public API paths, and sanitize credential-bearing errors before they reach logs, health output, MQTT attributes, or `state.json`.
- Rationale: this service is meant for self-hosting, not anti-bot experimentation, and provider error text can otherwise leak API keys or other secrets into operator-visible surfaces.
- Consequence: if a future provider requires browser automation, account-session reuse, proxy rotation, CAPTCHA solving, or Cloudflare bypass to work, it should be documented as unsupported instead of implemented.
