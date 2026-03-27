from __future__ import annotations

from datetime import UTC, datetime

from mlb_ticket_tracker.models import (
    MatchedEvent,
    PriceObservation,
    ProviderCapability,
    ProviderHealth,
    ScheduledGame,
    SourceStatus,
)
from mlb_ticket_tracker.providers.base import Provider
from mlb_ticket_tracker.service import _failure_health


class FakeProvider(Provider):
    source = "fake"

    def capability_report(self) -> ProviderCapability:
        return ProviderCapability(
            source="fake",
            source_status=SourceStatus.SUPPORTED,
            auth_required=False,
            implemented_fields=("price",),
            limitations=(),
        )

    def healthcheck(self) -> bool:
        return True

    def match_events(
        self,
        games: list[ScheduledGame],
        cached_matches: dict[str, MatchedEvent],
    ) -> dict[str, MatchedEvent]:
        del cached_matches
        return {
            f"fake:{game.game_id}": MatchedEvent(
                source="fake",
                game_id=game.game_id,
                source_event_id=f"fake-{game.game_pk}",
                matched_at=datetime(2026, 3, 27, tzinfo=UTC),
            )
            for game in games
        }

    def fetch_lowest_price(
        self,
        game: ScheduledGame,
        matched_event: MatchedEvent | None,
    ) -> PriceObservation:
        del matched_event
        return PriceObservation(
            source="fake",
            source_status=SourceStatus.SUPPORTED,
            game_id=game.game_id,
            game_datetime=game.game_datetime,
            home_team=game.home_team,
            away_team=game.away_team,
            venue=game.venue,
            currency="USD",
            cheapest_price=10.0,
            checked_at=datetime(2026, 3, 27, tzinfo=UTC),
        )


def test_failure_health_backoff_grows() -> None:
    first = _failure_health(
        previous=ProviderHealth(),
        now=datetime(2026, 3, 27, tzinfo=UTC),
        error="boom",
    )
    second = _failure_health(
        previous=first,
        now=datetime(2026, 3, 27, 0, 10, tzinfo=UTC),
        error="boom again",
    )

    assert first.consecutive_failures == 1
    assert second.consecutive_failures == 2
    assert second.backoff_until is not None
    assert first.backoff_until is not None
    assert second.backoff_until > first.backoff_until
