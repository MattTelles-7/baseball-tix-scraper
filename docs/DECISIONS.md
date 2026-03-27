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
