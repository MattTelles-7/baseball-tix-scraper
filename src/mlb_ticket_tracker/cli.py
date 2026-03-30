"""Command-line entry points."""

from __future__ import annotations

import argparse
import json

from mlb_ticket_tracker.config import load_settings
from mlb_ticket_tracker.health import evaluate_health
from mlb_ticket_tracker.logging import configure_logging
from mlb_ticket_tracker.service import TrackerService, build_service_context


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(prog="mlb-ticket-tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    healthcheck_parser = subparsers.add_parser("healthcheck")
    healthcheck_parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    """Execute the CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level)
    context = build_service_context(settings)

    if args.command == "run":
        TrackerService(context).run_forever()
        return 0

    if args.command == "healthcheck":
        state = context.state_store.load()
        report = evaluate_health(settings=settings, state=state)
        if args.json:
            print(json.dumps(report.to_dict(), sort_keys=True))
        else:
            print(f"{report.status}: {report.reason}")
        return 0 if report.ok else 1

    return parser.exit(status=2)


if __name__ == "__main__":
    raise SystemExit(main())
