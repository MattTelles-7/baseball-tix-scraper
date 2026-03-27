"""Provider interface definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mlb_ticket_tracker.models import (
    MatchedEvent,
    PriceObservation,
    ProviderCapability,
    ScheduledGame,
)


class Provider(ABC):
    """Abstract adapter for a ticket source."""

    source: str

    @abstractmethod
    def capability_report(self) -> ProviderCapability:
        """Describe the support level and limitations of this provider."""

    @abstractmethod
    def healthcheck(self) -> bool:
        """Return whether the provider is configured enough to attempt polling."""

    @abstractmethod
    def match_events(
        self,
        games: list[ScheduledGame],
        cached_matches: dict[str, MatchedEvent],
    ) -> dict[str, MatchedEvent]:
        """Find provider-specific events for the given games."""

    @abstractmethod
    def fetch_lowest_price(
        self,
        game: ScheduledGame,
        matched_event: MatchedEvent | None,
    ) -> PriceObservation:
        """Fetch the normalized cheapest-price observation for one game."""
