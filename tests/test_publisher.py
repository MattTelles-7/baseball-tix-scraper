from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.models import PriceObservation, ScheduledGame, TeamInfo, TrackerState
from mlb_ticket_tracker.publisher import (
    build_price_entity_descriptor,
    build_static_sensor_descriptor,
)
from mlb_ticket_tracker.state import StateStore
from tests.fakes import CapturingPublisher, seed_dynamic_entity


def test_build_price_entity_descriptor(
    settings_factory: Callable[..., Settings],
    reds_team: TeamInfo,
    home_game: ScheduledGame,
) -> None:
    descriptor = build_price_entity_descriptor(
        settings=settings_factory(),
        team=reds_team,
        game=home_game,
        source="ticketmaster",
        currency="USD",
    )

    assert descriptor.unique_id == "mlb_tix_cincinnati_reds_824540_ticketmaster_lowest_price"
    assert descriptor.discovery_topic == (
        "homeassistant/sensor/mlb_tix_cincinnati_reds_824540_ticketmaster_lowest_price/config"
    )
    assert descriptor.state_topic == "mlb_ticket_tracker/games/824540/ticketmaster/state"
    assert descriptor.attributes_topic == "mlb_ticket_tracker/games/824540/ticketmaster/attributes"


def test_build_static_sensor_descriptor(
    settings_factory: Callable[..., Settings],
    reds_team: TeamInfo,
) -> None:
    descriptor = build_static_sensor_descriptor(
        settings=settings_factory(),
        team=reds_team,
        sensor_key="next_poll",
        name="Next Poll",
        state_topic_suffix="service/next_poll",
        icon="mdi:clock-outline",
        device_class="timestamp",
    )

    assert descriptor.unique_id == "mlb_tix_cincinnati_reds_next_poll"
    assert descriptor.config_payload["device_class"] == "timestamp"


def test_publish_price_observation_emits_expected_topics(
    settings_factory: Callable[..., Settings],
    reds_team: TeamInfo,
    home_game: ScheduledGame,
    price_observation: PriceObservation,
    tmp_path: Path,
) -> None:
    settings = settings_factory()
    store = StateStore(tmp_path / "state.json")
    state = TrackerState()
    publisher = CapturingPublisher(settings)
    descriptor = build_price_entity_descriptor(
        settings=settings,
        team=reds_team,
        game=home_game,
        source="ticketmaster",
        currency="USD",
    )

    entity_id = publisher.publish_price_observation(
        team=reds_team,
        game=home_game,
        observation=price_observation,
        state_store=store,
        state=state,
    )

    assert entity_id == descriptor.unique_id
    assert state.dynamic_entities[descriptor.unique_id] == descriptor.discovery_topic
    assert {topic for topic, _, _ in publisher.published_messages} == {
        descriptor.discovery_topic,
        descriptor.state_topic,
        descriptor.attributes_topic,
    }
    assert all(retain is True for _, _, retain in publisher.published_messages)
    assert state.published_topics[descriptor.state_topic] == "24.50"

    assert descriptor.attributes_topic is not None
    attributes_payload = json.loads(state.published_topics[descriptor.attributes_topic])
    assert attributes_payload["opponent"] == "Boston Red Sox"
    assert attributes_payload["source_status"] == "supported"
    assert attributes_payload["source_event_id"] == "G5v123"


def test_publish_price_observation_deduplicates_identical_payloads(
    settings_factory: Callable[..., Settings],
    reds_team: TeamInfo,
    home_game: ScheduledGame,
    price_observation: PriceObservation,
    tmp_path: Path,
) -> None:
    publisher = CapturingPublisher(settings_factory())
    store = StateStore(tmp_path / "state.json")
    state = TrackerState()

    publisher.publish_price_observation(
        team=reds_team,
        game=home_game,
        observation=price_observation,
        state_store=store,
        state=state,
    )
    publisher.publish_price_observation(
        team=reds_team,
        game=home_game,
        observation=price_observation,
        state_store=store,
        state=state,
    )

    assert len(publisher.published_messages) == 3


def test_failed_publish_does_not_mark_topic_as_sent(
    settings_factory: Callable[..., Settings],
    reds_team: TeamInfo,
    home_game: ScheduledGame,
    price_observation: PriceObservation,
    tmp_path: Path,
) -> None:
    settings = settings_factory()
    publisher = CapturingPublisher(settings)
    store = StateStore(tmp_path / "state.json")
    state = TrackerState()
    descriptor = build_price_entity_descriptor(
        settings=settings,
        team=reds_team,
        game=home_game,
        source="ticketmaster",
        currency="USD",
    )
    publisher.failed_once_topics.add(descriptor.state_topic)

    with pytest.raises(RuntimeError, match="simulated publish failure"):
        publisher.publish_price_observation(
            team=reds_team,
            game=home_game,
            observation=price_observation,
            state_store=store,
            state=state,
        )

    assert descriptor.discovery_topic in state.published_topics
    assert descriptor.state_topic not in state.published_topics
    assert descriptor.attributes_topic not in state.published_topics
    assert descriptor.unique_id not in state.dynamic_entities

    publisher.publish_price_observation(
        team=reds_team,
        game=home_game,
        observation=price_observation,
        state_store=store,
        state=state,
    )

    assert state.published_topics[descriptor.state_topic] == "24.50"
    assert descriptor.unique_id in state.dynamic_entities


def test_cleanup_stale_dynamic_entities_only_removes_inactive_entities(
    settings_factory: Callable[..., Settings],
    tmp_path: Path,
) -> None:
    publisher = CapturingPublisher(settings_factory())
    store = StateStore(tmp_path / "state.json")
    state = TrackerState()
    active_unique_id = "mlb_tix_active"
    stale_unique_id = "mlb_tix_stale"
    active_topic = "homeassistant/sensor/mlb_tix_active/config"
    stale_topic = "homeassistant/sensor/mlb_tix_stale/config"
    seed_dynamic_entity(
        state_store=store,
        state=state,
        unique_id=active_unique_id,
        discovery_topic=active_topic,
    )
    seed_dynamic_entity(
        state_store=store,
        state=state,
        unique_id=stale_unique_id,
        discovery_topic=stale_topic,
    )
    store.track_published_topic(state, topic=active_topic, payload='{"name": "active"}')
    store.track_published_topic(state, topic=stale_topic, payload='{"name": "stale"}')

    publisher.cleanup_stale_dynamic_entities(
        active_unique_ids={active_unique_id},
        state_store=store,
        state=state,
    )

    assert state.dynamic_entities == {active_unique_id: active_topic}
    assert stale_topic not in state.published_topics
    assert publisher.published_messages == [(stale_topic, "", True)]
