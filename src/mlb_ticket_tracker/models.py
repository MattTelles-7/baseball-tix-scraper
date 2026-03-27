"""Shared domain models for schedule, provider, and runtime state."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SourceStatus(StrEnum):
    """Support and runtime status for a provider result."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    EXPERIMENTAL = "experimental"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class TeamInfo(BaseModel):
    """Static information about an MLB team."""

    model_config = ConfigDict(frozen=True)

    id: int
    slug: str
    name: str
    city: str
    venue: str
    aliases: tuple[str, ...] = ()


class ScheduledGame(BaseModel):
    """Normalized view of an MLB scheduled game."""

    model_config = ConfigDict(frozen=True)

    game_id: str
    game_pk: int
    game_datetime: datetime
    official_date: str
    home_team: str
    away_team: str
    venue: str
    timezone: str
    home_team_id: int
    away_team_id: int
    game_type: str
    status: str


class MatchedEvent(BaseModel):
    """Cached provider event match for a game."""

    source: str
    game_id: str
    source_event_id: str
    source_url: str | None = None
    matched_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class PriceObservation(BaseModel):
    """Normalized cheapest-price observation for a game/source pair."""

    source: str
    source_status: SourceStatus
    game_id: str
    game_datetime: datetime
    home_team: str
    away_team: str
    venue: str
    currency: str | None = None
    cheapest_price: float | None = None
    price_is_all_in: bool | None = None
    source_event_id: str | None = None
    source_url: str | None = None
    checked_at: datetime
    notes: str | None = None


class ProviderCapability(BaseModel):
    """Honest statement about a provider adapter's support level."""

    source: str
    source_status: SourceStatus
    auth_required: bool
    implemented_fields: tuple[str, ...]
    limitations: tuple[str, ...]


class ProviderHealth(BaseModel):
    """Persistent health metadata for a provider."""

    consecutive_failures: int = 0
    last_successful_poll_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None
    backoff_until: datetime | None = None


class RuntimeStatus(BaseModel):
    """Persistent runtime markers used for healthcheck and operations."""

    last_started_poll_at: datetime | None = None
    last_completed_poll_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    next_poll_at: datetime | None = None


class TrackerState(BaseModel):
    """JSON-serialized application state."""

    schema_version: int = 1
    published_topics: dict[str, str] = Field(default_factory=dict)
    dynamic_entities: dict[str, str] = Field(default_factory=dict)
    provider_matches: dict[str, MatchedEvent] = Field(default_factory=dict)
    provider_health: dict[str, ProviderHealth] = Field(default_factory=dict)
    runtime: RuntimeStatus = Field(default_factory=RuntimeStatus)
