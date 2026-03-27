"""SeatGeek provider scaffold."""

from __future__ import annotations

from datetime import UTC, datetime

from mlb_ticket_tracker.config import SeatGeekSettings
from mlb_ticket_tracker.models import (
    MatchedEvent,
    PriceObservation,
    ProviderCapability,
    ScheduledGame,
    SourceStatus,
)
from mlb_ticket_tracker.providers.base import Provider


class SeatGeekProvider(Provider):
    """Partial SeatGeek adapter scaffold, disabled by default."""

    source = "seatgeek"

    def __init__(self, settings: SeatGeekSettings) -> None:
        self._settings = settings

    def capability_report(self) -> ProviderCapability:
        return ProviderCapability(
            source=self.source,
            source_status=SourceStatus.PARTIAL,
            auth_required=True,
            implemented_fields=("stats.lowest_price",),
            limitations=(
                "Live listing-level parity is not yet verified for this personal-service use case.",
                "No all-in pricing field is currently modeled.",
            ),
        )

    def healthcheck(self) -> bool:
        return bool(self._settings.client_id)

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
            source_status=SourceStatus.PARTIAL,
            game_id=game.game_id,
            game_datetime=game.game_datetime,
            home_team=game.home_team,
            away_team=game.away_team,
            venue=game.venue,
            checked_at=datetime.now(tz=UTC),
            notes="SeatGeek support is scaffolded only and disabled by default in this release.",
        )
