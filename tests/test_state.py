from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from mlb_ticket_tracker.models import MatchedEvent, ProviderHealth, RuntimeStatus, TrackerState
from mlb_ticket_tracker.state import StateStore


def test_state_store_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    state = TrackerState()
    state.provider_matches["ticketmaster:mlb:824540"] = MatchedEvent(
        source="ticketmaster",
        game_id="mlb:824540",
        source_event_id="G5d",
        source_url="https://example.com",
        matched_at=datetime(2026, 3, 27, tzinfo=UTC),
    )
    state.provider_health["ticketmaster"] = ProviderHealth(consecutive_failures=1)
    state.runtime = RuntimeStatus(last_heartbeat_at=datetime(2026, 3, 27, tzinfo=UTC))

    store.save(state)
    loaded = store.load()

    assert loaded.provider_matches["ticketmaster:mlb:824540"].source_event_id == "G5d"
    assert loaded.provider_health["ticketmaster"].consecutive_failures == 1
    assert loaded.runtime.last_heartbeat_at == datetime(2026, 3, 27, tzinfo=UTC)


def test_track_published_topic_change_detection(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    state = TrackerState()

    first_change = store.track_published_topic(state, topic="topic/a", payload='{"value": 1}')
    second_change = store.track_published_topic(state, topic="topic/a", payload='{"value": 1}')
    third_change = store.track_published_topic(state, topic="topic/a", payload='{"value": 2}')

    assert first_change is True
    assert second_change is False
    assert third_change is True
