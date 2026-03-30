from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from stat import S_IMODE

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
    assert S_IMODE(path.stat().st_mode) == 0o600


def test_track_published_topic_change_detection(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    state = TrackerState()

    first_change = store.track_published_topic(state, topic="topic/a", payload='{"value": 1}')
    second_change = store.track_published_topic(state, topic="topic/a", payload='{"value": 1}')
    third_change = store.track_published_topic(state, topic="topic/a", payload='{"value": 2}')

    assert first_change is True
    assert second_change is False
    assert third_change is True


def test_state_store_load_returns_empty_state_for_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not-json", encoding="utf-8")
    store = StateStore(path)

    loaded = store.load()

    assert loaded == TrackerState()


def test_register_and_unregister_entity_and_topics(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    state = TrackerState()

    store.register_entity(
        state,
        unique_id="mlb_tix_cincinnati_reds_824540_ticketmaster_lowest_price",
        discovery_topic="homeassistant/sensor/example/config",
    )
    store.track_published_topic(
        state,
        topic="homeassistant/sensor/example/config",
        payload='{"name": "Example"}',
    )
    store.clear_published_topic(state, topic="homeassistant/sensor/example/config")
    store.unregister_entity(
        state,
        unique_id="mlb_tix_cincinnati_reds_824540_ticketmaster_lowest_price",
    )

    assert state.published_topics == {}
    assert state.dynamic_entities == {}
