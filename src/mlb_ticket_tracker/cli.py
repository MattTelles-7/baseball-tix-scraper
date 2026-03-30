"""Command-line entry points."""

from __future__ import annotations

import argparse
import json

from mlb_ticket_tracker.config import load_settings
from mlb_ticket_tracker.health import evaluate_health
from mlb_ticket_tracker.logging import configure_logging
from mlb_ticket_tracker.service import TrackerService, build_service_context
from mlb_ticket_tracker.validation import validate_settings


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(prog="mlb-ticket-tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    healthcheck_parser = subparsers.add_parser("healthcheck")
    healthcheck_parser.add_argument("--json", action="store_true")
    validate_parser = subparsers.add_parser("validate-config")
    validate_parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    """Execute the CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level)

    if args.command == "run":
        context = build_service_context(settings)
        TrackerService(context).run_forever()
        return 0

    if args.command == "healthcheck":
        context = build_service_context(settings)
        state = context.state_store.load()
        health_report = evaluate_health(settings=settings, state=state)
        if args.json:
            print(json.dumps(health_report.to_dict(), sort_keys=True))
        else:
            print(f"{health_report.status}: {health_report.reason}")
        return 0 if health_report.ok else 1

    if args.command == "validate-config":
        validation_report = validate_settings(settings)
        if args.json:
            print(json.dumps(validation_report.to_dict(), sort_keys=True))
        else:
            print(validation_report.summary)
            if validation_report.errors:
                print("Errors:")
                for item in validation_report.errors:
                    print(f"- {item}")
            if validation_report.warnings:
                print("Warnings:")
                for item in validation_report.warnings:
                    print(f"- {item}")
            print(f"Team: {validation_report.details['team']}")
            print(
                "Data dir: "
                f"{validation_report.details['data_dir']} "
                f"({validation_report.details['data_dir_status']})"
            )
            print(f"Dry run: {validation_report.details['dry_run']}")
        return 0 if validation_report.ok else 1

    return parser.exit(status=2)


if __name__ == "__main__":
    raise SystemExit(main())
