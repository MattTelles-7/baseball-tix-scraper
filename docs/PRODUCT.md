# Product

## Goal

Run a small self-hosted service that tracks upcoming MLB home games and publishes the cheapest currently available ticket price per game per source into Home Assistant.

## Primary User

One self-hosting user running the service for personal monitoring on a Debian 13 server.

## In Scope

- MLB team schedule lookup
- Home games only by default
- Ticketmaster support first
- MQTT discovery publishing for Home Assistant
- Lightweight local persistence
- Docker Compose deployment

## Out of Scope

- SQL-backed storage in v1
- Multi-user or SaaS features
- Notification workflows outside Home Assistant
- MLB Ballpark support
- Anti-bot or evasion features
