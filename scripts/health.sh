#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose exec mlb-ticket-tracker mlb-ticket-tracker healthcheck --json
