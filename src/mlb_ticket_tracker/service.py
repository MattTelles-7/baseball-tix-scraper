"""Service bootstrap helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import structlog

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.models import RuntimeStatus, TeamInfo, TrackerState
from mlb_ticket_tracker.schedule import MlbScheduleClient
from mlb_ticket_tracker.state import StateStore
from mlb_ticket_tracker.teams import resolve_team

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ServiceContext:
    """Resolved application dependencies used by the service."""

    settings: Settings
    team: TeamInfo
    state_store: StateStore
    schedule_client: MlbScheduleClient


def build_service_context(settings: Settings) -> ServiceContext:
    """Construct the baseline dependencies used by the app."""
    return ServiceContext(
        settings=settings,
        team=resolve_team(settings.team_id, settings.team_slug, settings.team_name),
        state_store=StateStore(settings.state_path),
        schedule_client=MlbScheduleClient(timeout_seconds=settings.http_timeout_seconds),
    )


def initialize_runtime_state(
    *,
    state_store: StateStore,
    state: TrackerState,
    poll_interval_minutes: int,
    timezone: str,
) -> TrackerState:
    """Initialize heartbeat and poll timing metadata at startup."""
    now = datetime.now(tz=ZoneInfo(timezone))
    runtime = RuntimeStatus(
        last_started_poll_at=state.runtime.last_started_poll_at,
        last_completed_poll_at=state.runtime.last_completed_poll_at,
        last_heartbeat_at=now,
        next_poll_at=now + timedelta(minutes=poll_interval_minutes),
    )
    updated_state = state_store.update_runtime(state, runtime)
    state_store.save(updated_state)
    next_poll_at = runtime.next_poll_at.isoformat() if runtime.next_poll_at else None
    logger.info("runtime_initialized", next_poll_at=next_poll_at)
    return updated_state
