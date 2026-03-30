"""Typed service ports for orchestration dependencies."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from mlb_ticket_tracker.models import (
    PriceObservation,
    ProviderCapability,
    ProviderHealth,
    ScheduledGame,
    TeamInfo,
    TrackerState,
)
from mlb_ticket_tracker.state import StateStore


class ScheduleClientPort(Protocol):
    """Schedule-fetching dependency used by the service."""

    def fetch_upcoming_games(
        self,
        *,
        team: TeamInfo,
        lookahead_days: int,
        home_games_only: bool,
        timezone: str,
        grace_minutes: int = 0,
        now: datetime | None = None,
    ) -> list[ScheduledGame]:
        """Fetch and normalize upcoming games for a team."""


class PublisherPort(Protocol):
    """Publishing dependency used by the service."""

    def connect(self) -> None:
        """Connect the publisher to its upstream broker or sink."""

    def close(self) -> None:
        """Close any upstream publisher resources."""

    def publish_price_observation(
        self,
        *,
        team: TeamInfo,
        game: ScheduledGame,
        observation: PriceObservation,
        state_store: StateStore,
        state: TrackerState,
    ) -> str:
        """Publish one normalized price observation."""

    def publish_provider_health(
        self,
        *,
        team: TeamInfo,
        capability: ProviderCapability,
        health: ProviderHealth,
        state_store: StateStore,
        state: TrackerState,
        healthy: bool,
        configured: bool,
    ) -> None:
        """Publish provider health information."""

    def publish_service_metrics(
        self,
        *,
        team: TeamInfo,
        tracked_games: int,
        next_poll_at: datetime,
        last_completed_poll_at: datetime | None,
        state_store: StateStore,
        state: TrackerState,
    ) -> None:
        """Publish service-level operational metrics."""

    def cleanup_stale_dynamic_entities(
        self,
        *,
        active_unique_ids: set[str],
        state_store: StateStore,
        state: TrackerState,
    ) -> None:
        """Remove stale dynamic entities from the publisher sink."""
