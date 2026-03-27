"""Command-line entry points."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from mlb_ticket_tracker.config import load_settings
from mlb_ticket_tracker.logging import configure_logging
from mlb_ticket_tracker.service import build_service_context, initialize_runtime_state


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(prog="mlb-ticket-tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    subparsers.add_parser("healthcheck")
    return parser


def main() -> int:
    """Execute the CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level)
    context = build_service_context(settings)

    if args.command == "run":
        state = context.state_store.load()
        initialize_runtime_state(
            state_store=context.state_store,
            state=state,
            poll_interval_minutes=settings.poll_interval_minutes,
            timezone=settings.timezone,
        )
        return 0

    if args.command == "healthcheck":
        state = context.state_store.load()
        heartbeat = state.runtime.last_heartbeat_at
        if heartbeat is None:
            return 1

        now = datetime.now(tz=ZoneInfo(settings.timezone))
        allowed_staleness = timedelta(minutes=(settings.poll_interval_minutes * 2) + 5)
        return 0 if now - heartbeat <= allowed_staleness else 1

    return parser.exit(status=2)


if __name__ == "__main__":
    raise SystemExit(main())
