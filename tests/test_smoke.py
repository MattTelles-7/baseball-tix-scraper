from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.models import (
    MatchedEvent,
    PriceObservation,
    ProviderCapability,
    ProviderHealth,
    ScheduledGame,
    SourceStatus,
    TeamInfo,
    TrackerState,
)
from mlb_ticket_tracker.providers.base import Provider
from mlb_ticket_tracker.publisher import MqttPublisher
from mlb_ticket_tracker.schedule import MlbScheduleClient
from mlb_ticket_tracker.service import ServiceContext, TrackerService
from mlb_ticket_tracker.state import StateStore


class FakeScheduleClient:
    def __init__(self, games: list[ScheduledGame]) -> None:
        self.games = games

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
        del team, lookahead_days, home_games_only, timezone, grace_minutes, now
        return self.games


class FakeProvider(Provider):
    source = "fake"

    def capability_report(self) -> ProviderCapability:
        return ProviderCapability(
            source=self.source,
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
            f"{self.source}:{game.game_id}": MatchedEvent(
                source=self.source,
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
            source=self.source,
            source_status=SourceStatus.SUPPORTED,
            game_id=game.game_id,
            game_datetime=game.game_datetime,
            home_team=game.home_team,
            away_team=game.away_team,
            venue=game.venue,
            currency="USD",
            cheapest_price=11.5,
            checked_at=datetime(2026, 3, 27, tzinfo=UTC),
        )


class FakePublisher:
    def __init__(self) -> None:
        self.price_entities: list[str] = []
        self.provider_health_calls: list[tuple[str, bool, bool]] = []
        self.metrics_calls: list[tuple[int, datetime, datetime | None]] = []
        self.cleaned_active_ids: set[str] | None = None

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def publish_price_observation(
        self,
        *,
        team: TeamInfo,
        game: ScheduledGame,
        observation: PriceObservation,
        state_store: StateStore,
        state: TrackerState,
    ) -> str:
        del team, game, observation, state_store, state
        entity_id = "fake_entity"
        self.price_entities.append(entity_id)
        return entity_id

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
        del team, health, state_store, state
        self.provider_health_calls.append((capability.source, healthy, configured))

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
        del team, state_store, state
        self.metrics_calls.append((tracked_games, next_poll_at, last_completed_poll_at))

    def cleanup_stale_dynamic_entities(
        self,
        *,
        active_unique_ids: set[str],
        state_store: StateStore,
        state: TrackerState,
    ) -> None:
        del state_store, state
        self.cleaned_active_ids = active_unique_ids


def test_tracker_service_smoke_cycle(tmp_path: Path) -> None:
    settings = Settings.model_validate(
        {
            "TEAM_ID": 113,
            "MQTT_HOST": "mqtt.local",
            "MQTT_PORT": 1883,
            "POLL_INTERVAL_MINUTES": 15,
            "POST_GAME_GRACE_MINUTES": 240,
            "ENABLE_TICKETMASTER": False,
            "DATA_DIR": str(tmp_path),
        }
    )
    team = TeamInfo(
        id=113,
        slug="cincinnati-reds",
        name="Cincinnati Reds",
        city="Cincinnati",
        venue="Great American Ball Park",
    )
    game = ScheduledGame(
        game_id="mlb:824540",
        game_pk=824540,
        game_datetime=datetime(2026, 3, 28, 20, 10, tzinfo=UTC),
        official_date="2026-03-28",
        home_team="Cincinnati Reds",
        away_team="Boston Red Sox",
        venue="Great American Ball Park",
        timezone="America/New_York",
        home_team_id=113,
        away_team_id=111,
        game_type="R",
        status="Scheduled",
    )
    state_store = StateStore(tmp_path / "state.json")
    context = ServiceContext(
        settings=settings,
        team=team,
        state_store=state_store,
        schedule_client=cast(MlbScheduleClient, FakeScheduleClient([game])),
    )
    service = TrackerService(context)
    fake_publisher = FakePublisher()
    service._publisher = cast(MqttPublisher, fake_publisher)
    service._providers = [FakeProvider()]

    updated_state = service._run_cycle(
        state=TrackerState(),
        cycle_started=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
    )
    persisted_state = state_store.load()

    assert fake_publisher.price_entities == ["fake_entity"]
    assert fake_publisher.cleaned_active_ids == {"fake_entity"}
    assert fake_publisher.provider_health_calls == [("fake", True, True)]
    assert fake_publisher.metrics_calls[0][0] == 1
    assert "fake:mlb:824540" in updated_state.provider_matches
    assert "fake:mlb:824540" in persisted_state.provider_matches
    assert persisted_state.provider_health["fake"].consecutive_failures == 0
    assert persisted_state.runtime.last_completed_poll_at is not None
