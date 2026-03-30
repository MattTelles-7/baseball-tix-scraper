#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo ".env not found. Copy .env.example to .env and fill in the required values." >&2
  exit 1
fi

docker compose --env-file .env run --rm mlb-ticket-tracker validate-config --json
