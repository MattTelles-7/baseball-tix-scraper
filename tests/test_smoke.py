from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.models import ScheduledGame, TeamInfo, TrackerState
from mlb_ticket_tracker.publisher import build_price_entity_descriptor
from mlb_ticket_tracker.service import ServiceContext, TrackerService
from mlb_ticket_tracker.state import StateStore
from tests.fakes import CapturingPublisher, FakeScheduleClient, StaticProvider


def test_tracker_service_smoke_cycle_publishes_and_deduplicates(
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
    provider = StaticProvider(source="ticketmaster", price=24.5)
    publisher = CapturingPublisher(settings)
    service._publisher = publisher
    service._providers = [provider]

    first_state = service._run_cycle(
        state=TrackerState(),
        cycle_started=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
    )
    persisted_state = state_store.load()
    descriptor = build_price_entity_descriptor(
        settings=settings,
        team=reds_team,
        game=home_game,
        source="ticketmaster",
        currency="USD",
    )
    published_topics = {topic: payload for topic, payload, _ in publisher.published_messages}

    assert "ticketmaster:mlb:824540" in first_state.provider_matches
    assert "ticketmaster:mlb:824540" in persisted_state.provider_matches
    assert persisted_state.provider_health["ticketmaster"].consecutive_failures == 0
    assert persisted_state.runtime.last_completed_poll_at is not None
    assert published_topics[descriptor.state_topic] == "24.50"
    assert descriptor.unique_id in persisted_state.dynamic_entities

    assert descriptor.attributes_topic is not None
    attributes_payload = json.loads(published_topics[descriptor.attributes_topic])
    assert attributes_payload["source"] == "ticketmaster"
    assert attributes_payload["opponent"] == "Boston Red Sox"
    assert published_topics["mlb_ticket_tracker/providers/ticketmaster/health/state"] == "healthy"
    assert published_topics["mlb_ticket_tracker/service/tracked_home_games/state"] == "1"

    publisher.published_messages.clear()
    second_state = service._run_cycle(
        state=persisted_state,
        cycle_started=datetime(2026, 3, 27, 12, 15, tzinfo=UTC),
    )

    assert second_state.provider_health["ticketmaster"].consecutive_failures == 0
    assert not any(
        topic.startswith("mlb_ticket_tracker/games/824540/ticketmaster/")
        for topic, _, _ in publisher.published_messages
    )
