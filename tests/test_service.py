from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

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
from mlb_ticket_tracker.publisher import build_price_entity_descriptor
from mlb_ticket_tracker.service import ServiceContext, TrackerService, _failure_health
from mlb_ticket_tracker.state import StateStore
from tests.fakes import (
    CapturingPublisher,
    ExplodingProvider,
    FakeScheduleClient,
    StaticProvider,
    seed_dynamic_entity,
)


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


def test_run_cycle_records_provider_failure_and_continues(
    settings_factory: Callable[..., Settings],
    reds_team: TeamInfo,
    home_game: ScheduledGame,
    tmp_path: Path,
) -> None:
    settings = settings_factory(
        ENABLE_TICKETMASTER=False,
        ENABLE_SEATGEEK=False,
        ENABLE_VIVID=False,
    )
    state_store = StateStore(tmp_path / "state.json")
    context = ServiceContext(
        settings=settings,
        team=reds_team,
        state_store=state_store,
        schedule_client=FakeScheduleClient([home_game]),
    )
    service = TrackerService(context)
    publisher = CapturingPublisher(settings)
    failing_provider = ExplodingProvider(source="broken", fail_on="fetch")
    healthy_provider = StaticProvider(source="steady", price=18.5)
    service._publisher = publisher
    service._providers = [failing_provider, healthy_provider]

    updated_state = service._run_cycle(
        state=TrackerState(),
        cycle_started=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
    )

    assert updated_state.provider_health["broken"].consecutive_failures == 1
    assert updated_state.provider_health["steady"].consecutive_failures == 0
    assert healthy_provider.fetch_calls == 1
    assert "steady:mlb:824540" in updated_state.provider_matches
    published_topics = {topic: payload for topic, payload, _ in publisher.published_messages}
    assert published_topics["mlb_ticket_tracker/providers/broken/health/state"] == "backoff"
    assert published_topics["mlb_ticket_tracker/providers/steady/health/state"] == "healthy"
    assert published_topics["mlb_ticket_tracker/games/824540/steady/state"] == "18.50"


def test_run_cycle_preserves_dynamic_entity_during_provider_backoff(
    settings_factory: Callable[..., Settings],
    reds_team: TeamInfo,
    home_game: ScheduledGame,
    tmp_path: Path,
) -> None:
    settings = settings_factory(
        ENABLE_TICKETMASTER=False,
        ENABLE_SEATGEEK=False,
        ENABLE_VIVID=False,
    )
    state_store = StateStore(tmp_path / "state.json")
    context = ServiceContext(
        settings=settings,
        team=reds_team,
        state_store=state_store,
        schedule_client=FakeScheduleClient([home_game]),
    )
    service = TrackerService(context)
    publisher = CapturingPublisher(settings)
    provider = StaticProvider(source="broken")
    service._publisher = publisher
    service._providers = [provider]

    descriptor = build_price_entity_descriptor(
        settings=settings,
        team=reds_team,
        game=home_game,
        source=provider.source,
        currency=None,
    )
    state = TrackerState(
        provider_health={
            provider.source: ProviderHealth(
                consecutive_failures=1,
                backoff_until=datetime(2026, 3, 27, 12, 5, tzinfo=UTC),
            )
        }
    )
    seed_dynamic_entity(
        state_store=state_store,
        state=state,
        unique_id=descriptor.unique_id,
        discovery_topic=descriptor.discovery_topic,
    )
    state_store.track_published_topic(
        state,
        topic=descriptor.discovery_topic,
        payload='{"name": "existing"}',
    )

    updated_state = service._run_cycle(
        state=state,
        cycle_started=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
    )

    assert provider.match_calls == 0
    assert provider.fetch_calls == 0
    assert descriptor.unique_id in updated_state.dynamic_entities
    published_topics = {topic: payload for topic, payload, _ in publisher.published_messages}
    assert published_topics["mlb_ticket_tracker/providers/broken/health/state"] == "backoff"


def test_run_forever_retries_after_mqtt_connect_failure(
    settings_factory: Callable[..., Settings],
    reds_team: TeamInfo,
    home_game: ScheduledGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = settings_factory(
        ENABLE_TICKETMASTER=False,
        ENABLE_SEATGEEK=False,
        ENABLE_VIVID=False,
        FAILURE_RETRY_SECONDS=7.5,
    )
    state_store = StateStore(tmp_path / "state.json")
    context = ServiceContext(
        settings=settings,
        team=reds_team,
        state_store=state_store,
        schedule_client=FakeScheduleClient([home_game]),
    )
    service = TrackerService(context)
    sleep_calls: list[float] = []

    class StopLoopError(RuntimeError):
        pass

    class ConnectFailingPublisher:
        def __init__(self) -> None:
            self.connect_calls = 0
            self.close_calls = 0

        def connect(self) -> None:
            self.connect_calls += 1
            msg = "mqtt unavailable"
            raise RuntimeError(msg)

        def close(self) -> None:
            self.close_calls += 1

    publisher = ConnectFailingPublisher()
    service._publisher = publisher  # type: ignore[assignment]
    service._providers = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        raise StopLoopError

    monkeypatch.setattr("mlb_ticket_tracker.service.time.sleep", fake_sleep)

    with pytest.raises(StopLoopError):
        service.run_forever()

    state = state_store.load()

    assert publisher.connect_calls == 1
    assert publisher.close_calls == 1
    assert sleep_calls == [7.5]
    assert state.runtime.last_error == "mqtt unavailable"
    assert state.runtime.last_error_at is not None
    assert state.runtime.next_poll_at is not None
