from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.models import (
    MatchedEvent,
    PriceObservation,
    ProviderCapability,
    ScheduledGame,
    SourceStatus,
    TeamInfo,
    TrackerState,
)
from mlb_ticket_tracker.providers.base import Provider
from mlb_ticket_tracker.publisher import MqttPublisher
from mlb_ticket_tracker.schedule import MlbScheduleClient
from mlb_ticket_tracker.state import StateStore


class FakeScheduleClient(MlbScheduleClient):
    def __init__(self, games: list[ScheduledGame]) -> None:
        super().__init__(timeout_seconds=1.0)
        self.games = games
        self.calls: list[dict[str, object]] = []

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
        self.calls.append(
            {
                "team": team,
                "lookahead_days": lookahead_days,
                "home_games_only": home_games_only,
                "timezone": timezone,
                "grace_minutes": grace_minutes,
                "now": now,
            }
        )
        return self.games


class StaticProvider(Provider):
    def __init__(
        self,
        *,
        source: str = "fake",
        status: SourceStatus = SourceStatus.SUPPORTED,
        price: float = 11.5,
        configured: bool = True,
        auth_required: bool = False,
        limitations: tuple[str, ...] = (),
    ) -> None:
        self.source = source
        self._status = status
        self._price = price
        self._configured = configured
        self._auth_required = auth_required
        self._limitations = limitations
        self.match_calls = 0
        self.fetch_calls = 0

    def capability_report(self) -> ProviderCapability:
        return ProviderCapability(
            source=self.source,
            source_status=self._status,
            auth_required=self._auth_required,
            implemented_fields=("price",),
            limitations=self._limitations,
        )

    def healthcheck(self) -> bool:
        return self._configured

    def match_events(
        self,
        games: list[ScheduledGame],
        cached_matches: dict[str, MatchedEvent],
    ) -> dict[str, MatchedEvent]:
        del cached_matches
        self.match_calls += 1
        return {
            f"{self.source}:{game.game_id}": MatchedEvent(
                source=self.source,
                game_id=game.game_id,
                source_event_id=f"{self.source}-{game.game_pk}",
                matched_at=datetime(2026, 3, 27, tzinfo=UTC),
            )
            for game in games
        }

    def fetch_lowest_price(
        self,
        game: ScheduledGame,
        matched_event: MatchedEvent | None,
    ) -> PriceObservation:
        self.fetch_calls += 1
        return PriceObservation(
            source=self.source,
            source_status=self._status,
            game_id=game.game_id,
            game_datetime=game.game_datetime,
            home_team=game.home_team,
            away_team=game.away_team,
            venue=game.venue,
            currency="USD",
            cheapest_price=self._price,
            source_event_id=matched_event.source_event_id if matched_event else None,
            source_url="https://example.test/tickets",
            checked_at=datetime(2026, 3, 27, tzinfo=UTC),
        )


class ExplodingProvider(StaticProvider):
    def __init__(self, *, source: str = "fake", fail_on: str = "fetch") -> None:
        super().__init__(source=source)
        self._fail_on = fail_on

    def match_events(
        self,
        games: list[ScheduledGame],
        cached_matches: dict[str, MatchedEvent],
    ) -> dict[str, MatchedEvent]:
        if self._fail_on == "match":
            msg = f"{self.source} match failed"
            raise RuntimeError(msg)
        return super().match_events(games, cached_matches)

    def fetch_lowest_price(
        self,
        game: ScheduledGame,
        matched_event: MatchedEvent | None,
    ) -> PriceObservation:
        if self._fail_on == "fetch":
            msg = f"{self.source} fetch failed"
            raise RuntimeError(msg)
        return super().fetch_lowest_price(game, matched_event)


class CapturingPublisher(MqttPublisher):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.published_messages: list[tuple[str, str, bool]] = []
        self.failed_once_topics: set[str] = set()
        self._already_failed_topics: set[str] = set()

    def _publish_raw(self, topic: str, payload: str, *, retain: bool) -> None:
        if topic in self.failed_once_topics and topic not in self._already_failed_topics:
            self._already_failed_topics.add(topic)
            msg = f"simulated publish failure for {topic}"
            raise RuntimeError(msg)
        self.published_messages.append((topic, payload, retain))


def seed_dynamic_entity(
    *,
    state_store: StateStore,
    state: TrackerState,
    unique_id: str,
    discovery_topic: str,
) -> None:
    state_store.register_entity(state, unique_id=unique_id, discovery_topic=discovery_topic)


def state_file(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path / "state.json")
