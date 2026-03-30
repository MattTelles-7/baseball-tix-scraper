"""Health evaluation helpers for container and operator checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.models import ProviderHealth, TrackerState
from mlb_ticket_tracker.utils import redact_sensitive_text


@dataclass(frozen=True)
class HealthReport:
    """Simple health report for CLI and container health checks."""

    ok: bool
    status: str
    reason: str
    checked_at: str
    details: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Convert the report into a JSON-serializable dictionary."""
        return asdict(self)


def evaluate_health(
    *,
    settings: Settings,
    state: TrackerState,
    now: datetime | None = None,
) -> HealthReport:
    """Assess service liveness from persisted runtime state."""
    current_time = now or datetime.now(tz=ZoneInfo(settings.timezone))
    heartbeat = state.runtime.last_heartbeat_at
    checked_at = current_time.isoformat()
    details: dict[str, object] = {
        "last_started_poll_at": _dt_to_str(state.runtime.last_started_poll_at),
        "last_completed_poll_at": _dt_to_str(state.runtime.last_completed_poll_at),
        "last_heartbeat_at": _dt_to_str(heartbeat),
        "next_poll_at": _dt_to_str(state.runtime.next_poll_at),
        "last_error_at": _dt_to_str(state.runtime.last_error_at),
        "last_error": (
            redact_sensitive_text(state.runtime.last_error)
            if state.runtime.last_error is not None
            else None
        ),
        "provider_health": {
            source: _provider_health_details(health)
            for source, health in state.provider_health.items()
        },
    }
    if heartbeat is None:
        return HealthReport(
            ok=False,
            status="starting",
            reason="no heartbeat has been recorded yet",
            checked_at=checked_at,
            details=details,
        )

    allowed_staleness = timedelta(minutes=(settings.poll_interval_minutes * 2) + 5)
    heartbeat_age = current_time - heartbeat.astimezone(current_time.tzinfo)
    details["heartbeat_age_seconds"] = round(heartbeat_age.total_seconds(), 3)
    details["allowed_staleness_seconds"] = allowed_staleness.total_seconds()

    if heartbeat_age > allowed_staleness:
        return HealthReport(
            ok=False,
            status="stale",
            reason="heartbeat is older than the allowed staleness window",
            checked_at=checked_at,
            details=details,
        )

    return HealthReport(
        ok=True,
        status="ok",
        reason="heartbeat is fresh",
        checked_at=checked_at,
        details=details,
    )


def _provider_health_details(health: ProviderHealth) -> dict[str, object]:
    return {
        "consecutive_failures": health.consecutive_failures,
        "last_successful_poll_at": _dt_to_str(health.last_successful_poll_at),
        "last_error_at": _dt_to_str(health.last_error_at),
        "last_error": (
            redact_sensitive_text(health.last_error) if health.last_error is not None else None
        ),
        "backoff_until": _dt_to_str(health.backoff_until),
    }


def _dt_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
