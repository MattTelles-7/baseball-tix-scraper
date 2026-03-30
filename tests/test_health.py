from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.health import evaluate_health
from mlb_ticket_tracker.models import ProviderHealth, RuntimeStatus, TrackerState


def test_evaluate_health_is_ok_with_fresh_heartbeat(
    settings_factory: Callable[..., Settings],
) -> None:
    settings = settings_factory(POLL_INTERVAL_MINUTES=15)
    state = TrackerState(
        runtime=RuntimeStatus(
            last_heartbeat_at=datetime(2026, 3, 29, 12, 0, tzinfo=UTC),
            last_completed_poll_at=datetime(2026, 3, 29, 11, 55, tzinfo=UTC),
        ),
        provider_health={"ticketmaster": ProviderHealth(consecutive_failures=0)},
    )

    report = evaluate_health(
        settings=settings,
        state=state,
        now=datetime(2026, 3, 29, 12, 20, tzinfo=UTC),
    )

    assert report.ok is True
    assert report.status == "ok"
    assert report.details["last_completed_poll_at"] == "2026-03-29T11:55:00+00:00"


def test_evaluate_health_fails_without_heartbeat(
    settings_factory: Callable[..., Settings],
) -> None:
    report = evaluate_health(
        settings=settings_factory(),
        state=TrackerState(),
        now=datetime(2026, 3, 29, 12, 0, tzinfo=UTC),
    )

    assert report.ok is False
    assert report.status == "starting"
    assert report.reason == "no heartbeat has been recorded yet"


def test_evaluate_health_fails_with_stale_heartbeat_and_reports_error(
    settings_factory: Callable[..., Settings],
) -> None:
    settings = settings_factory(POLL_INTERVAL_MINUTES=10)
    state = TrackerState(
        runtime=RuntimeStatus(
            last_heartbeat_at=datetime(2026, 3, 29, 11, 0, tzinfo=UTC),
            last_error_at=datetime(2026, 3, 29, 11, 5, tzinfo=UTC),
            last_error="mqtt down",
        ),
    )

    report = evaluate_health(
        settings=settings,
        state=state,
        now=datetime(2026, 3, 29, 12, 0, tzinfo=UTC),
    )

    assert report.ok is False
    assert report.status == "stale"
    assert report.details["last_error"] == "mqtt down"
    assert report.details["heartbeat_age_seconds"] == 3600.0
