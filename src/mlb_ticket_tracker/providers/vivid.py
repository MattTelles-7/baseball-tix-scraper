"""Vivid Seats provider scaffold."""

from __future__ import annotations

from datetime import UTC, datetime

from mlb_ticket_tracker.config import VividSettings
from mlb_ticket_tracker.models import (
    MatchedEvent,
    PriceObservation,
    ProviderCapability,
    ScheduledGame,
    SourceStatus,
)
from mlb_ticket_tracker.providers.base import Provider


class VividProvider(Provider):
    """Unsupported-by-default Vivid adapter scaffold."""

    source = "vivid"

    def __init__(self, settings: VividSettings) -> None:
        self._settings = settings

    def capability_report(self) -> ProviderCapability:
        return ProviderCapability(
            source=self.source,
            source_status=SourceStatus.UNAVAILABLE,
            auth_required=True,
            implemented_fields=(),
            limitations=(
                "Current branch does not implement a clean buyer-facing Vivid integration.",
                "Visible official docs are broker-oriented, so this source remains scaffold only.",
            ),
        )

    def healthcheck(self) -> bool:
        return self._settings.enabled and self._settings.api_token is not None

    def match_events(
        self,
        games: list[ScheduledGame],
        cached_matches: dict[str, MatchedEvent],
    ) -> dict[str, MatchedEvent]:
        del games, cached_matches
        return {}

    def fetch_lowest_price(
        self,
        game: ScheduledGame,
        matched_event: MatchedEvent | None,
    ) -> PriceObservation:
        del matched_event
        return PriceObservation(
            source=self.source,
            source_status=SourceStatus.UNAVAILABLE,
            game_id=game.game_id,
            game_datetime=game.game_datetime,
            home_team=game.home_team,
            away_team=game.away_team,
            venue=game.venue,
            checked_at=datetime.now(tz=UTC),
            notes="Vivid support is scaffolded only and remains unsupported by default.",
        )
