from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.models import (
    PriceObservation,
    ScheduledGame,
    SourceStatus,
    TeamInfo,
    TrackerState,
)
from mlb_ticket_tracker.publisher import (
    build_price_entity_descriptor,
    build_static_sensor_descriptor,
)
from mlb_ticket_tracker.state import StateStore


def _settings() -> Settings:
    return Settings.model_validate(
        {
            "TEAM_ID": 113,
            "MQTT_HOST": "mqtt.local",
            "MQTT_PORT": 1883,
            "MQTT_TOPIC_PREFIX": "mlb_ticket_tracker",
            "MQTT_DISCOVERY_PREFIX": "homeassistant",
        }
    )


def _team() -> TeamInfo:
    return TeamInfo(
        id=113,
        slug="cincinnati-reds",
        name="Cincinnati Reds",
        city="Cincinnati",
        venue="Great American Ball Park",
    )


def _game() -> ScheduledGame:
    return ScheduledGame(
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


def test_build_price_entity_descriptor() -> None:
    descriptor = build_price_entity_descriptor(
        settings=_settings(),
        team=_team(),
        game=_game(),
        source="ticketmaster",
        currency="USD",
    )

    assert descriptor.unique_id == "mlb_tix_cincinnati_reds_824540_ticketmaster_lowest_price"
    assert descriptor.discovery_topic == (
        "homeassistant/sensor/mlb_tix_cincinnati_reds_824540_ticketmaster_lowest_price/config"
    )
    assert descriptor.state_topic == "mlb_ticket_tracker/games/824540/ticketmaster/state"
    assert descriptor.attributes_topic == "mlb_ticket_tracker/games/824540/ticketmaster/attributes"


def test_build_static_sensor_descriptor() -> None:
    descriptor = build_static_sensor_descriptor(
        settings=_settings(),
        team=_team(),
        sensor_key="next_poll",
        name="Next Poll",
        state_topic_suffix="service/next_poll",
        icon="mdi:clock-outline",
        device_class="timestamp",
    )

    assert descriptor.unique_id == "mlb_tix_cincinnati_reds_next_poll"
    assert descriptor.config_payload["device_class"] == "timestamp"


def test_track_published_topics_for_price_sensor(tmp_path: Path) -> None:
    settings = _settings()
    descriptor = build_price_entity_descriptor(
        settings=settings,
        team=_team(),
        game=_game(),
        source="ticketmaster",
        currency="USD",
    )
    store = StateStore(tmp_path / "state.json")
    state = TrackerState()
    observation = PriceObservation(
        source="ticketmaster",
        source_status=SourceStatus.SUPPORTED,
        game_id="mlb:824540",
        game_datetime=_game().game_datetime,
        home_team="Cincinnati Reds",
        away_team="Boston Red Sox",
        venue="Great American Ball Park",
        currency="USD",
        cheapest_price=24.5,
        price_is_all_in=False,
        source_event_id="G5v123",
        source_url="https://ticketmaster.test/event",
        checked_at=datetime(2026, 3, 27, tzinfo=UTC),
        notes="Uses Discovery API minimum price.",
    )

    config_changed = store.track_published_topic(
        state,
        topic=descriptor.discovery_topic,
        payload=str(descriptor.config_payload),
    )
    state_changed = store.track_published_topic(
        state,
        topic=descriptor.state_topic,
        payload=f"{observation.cheapest_price:.2f}",
    )

    assert config_changed is True
    assert state_changed is True
