"""MQTT publishing helpers for Home Assistant discovery and state topics."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt
import structlog

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.models import (
    PriceObservation,
    ProviderCapability,
    ProviderHealth,
    ScheduledGame,
    TeamInfo,
    TrackerState,
)
from mlb_ticket_tracker.state import StateStore
from mlb_ticket_tracker.utils import redact_sensitive_text, slugify

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class EntityDescriptor:
    """Full MQTT topic identity and discovery payload for an entity."""

    unique_id: str
    discovery_topic: str
    state_topic: str
    attributes_topic: str | None
    config_payload: dict[str, Any]


def build_price_entity_descriptor(
    *,
    settings: Settings,
    team: TeamInfo,
    game: ScheduledGame,
    source: str,
    currency: str | None,
) -> EntityDescriptor:
    """Build MQTT topics and discovery config for a game price sensor."""
    entity_slug = slugify(f"{team.slug}_{game.game_pk}_{source}_lowest_price")
    unique_id = f"mlb_tix_{entity_slug}"
    state_topic = f"{settings.mqtt_topic_prefix}/games/{game.game_pk}/{source}/state"
    attributes_topic = f"{settings.mqtt_topic_prefix}/games/{game.game_pk}/{source}/attributes"
    discovery_topic = f"{settings.mqtt_discovery_prefix}/sensor/{unique_id}/config"
    config_payload: dict[str, Any] = {
        "name": f"{game.official_date} vs {game.away_team} {source.title()} Price",
        "unique_id": unique_id,
        "default_entity_id": f"sensor.{entity_slug}",
        "state_topic": state_topic,
        "json_attributes_topic": attributes_topic,
        "availability_topic": f"{settings.mqtt_topic_prefix}/availability",
        "unit_of_measurement": currency or "USD",
        "icon": "mdi:ticket-confirmation-outline",
        "state_class": "measurement",
        "suggested_display_precision": 2,
        "device": build_device_payload(team),
    }
    return EntityDescriptor(
        unique_id=unique_id,
        discovery_topic=discovery_topic,
        state_topic=state_topic,
        attributes_topic=attributes_topic,
        config_payload=config_payload,
    )


def build_static_sensor_descriptor(
    *,
    settings: Settings,
    team: TeamInfo,
    sensor_key: str,
    name: str,
    state_topic_suffix: str,
    icon: str,
    attributes: bool = False,
    unit_of_measurement: str | None = None,
    device_class: str | None = None,
    entity_category: str | None = None,
    options: list[str] | None = None,
) -> EntityDescriptor:
    """Build MQTT topics and discovery config for a static service sensor."""
    entity_slug = slugify(f"{team.slug}_{sensor_key}")
    unique_id = f"mlb_tix_{entity_slug}"
    state_topic = f"{settings.mqtt_topic_prefix}/{state_topic_suffix}/state"
    attributes_topic = (
        f"{settings.mqtt_topic_prefix}/{state_topic_suffix}/attributes" if attributes else None
    )
    discovery_topic = f"{settings.mqtt_discovery_prefix}/sensor/{unique_id}/config"
    config_payload: dict[str, Any] = {
        "name": name,
        "unique_id": unique_id,
        "default_entity_id": f"sensor.{entity_slug}",
        "state_topic": state_topic,
        "availability_topic": f"{settings.mqtt_topic_prefix}/availability",
        "icon": icon,
        "device": build_device_payload(team),
    }
    if attributes_topic:
        config_payload["json_attributes_topic"] = attributes_topic
    if unit_of_measurement is not None:
        config_payload["unit_of_measurement"] = unit_of_measurement
    if device_class is not None:
        config_payload["device_class"] = device_class
    if entity_category is not None:
        config_payload["entity_category"] = entity_category
    if options is not None:
        config_payload["options"] = options
    return EntityDescriptor(
        unique_id=unique_id,
        discovery_topic=discovery_topic,
        state_topic=state_topic,
        attributes_topic=attributes_topic,
        config_payload=config_payload,
    )


def build_device_payload(team: TeamInfo) -> dict[str, object]:
    """Build the Home Assistant device block shared across all entities."""
    return {
        "identifiers": [f"mlb-ticket-tracker-{team.slug}"],
        "name": f"{team.name} Ticket Tracker",
        "manufacturer": "Self-hosted",
        "model": "MLB Home Ticket Tracker",
        "sw_version": "0.1.0",
    }


class MqttPublisher:
    """Publish discovery and state payloads to Home Assistant via MQTT."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._dry_run = settings.dry_run
        self._connected = False
        self._loop_started = False
        self._client: mqtt.Client | None
        if self._dry_run:
            self._client = None
        else:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,  # type: ignore[attr-defined]
                client_id=settings.mqtt_client_id,
            )
            if settings.mqtt_username:
                client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
            client.enable_logger()
            client.reconnect_delay_set(min_delay=1, max_delay=30)
            client.will_set(
                f"{settings.mqtt_topic_prefix}/availability",
                payload="offline",
                qos=1,
                retain=True,
            )
            self._client = client

    def connect(self) -> None:
        """Connect to the MQTT broker and mark the app as online."""
        if self._dry_run:
            logger.info("mqtt_dry_run_mode")
            return
        if self._connected:
            return
        if self._client is None:
            msg = "MQTT client is not configured"
            raise RuntimeError(msg)
        logger.info(
            "mqtt_connecting",
            host=self._settings.mqtt_host,
            port=self._settings.mqtt_port,
            client_id=self._settings.mqtt_client_id,
        )
        try:
            if self._loop_started:
                self._client.reconnect()
            else:
                self._client.connect(
                    host=self._settings.mqtt_host,
                    port=self._settings.mqtt_port,
                    keepalive=self._settings.mqtt_keepalive,
                )
                self._client.loop_start()
                self._loop_started = True
            self._connected = True
            self._publish_raw(
                f"{self._settings.mqtt_topic_prefix}/availability",
                "online",
                retain=True,
            )
            logger.info(
                "mqtt_connected",
                host=self._settings.mqtt_host,
                port=self._settings.mqtt_port,
            )
        except Exception:
            self._connected = False
            logger.error("mqtt_connect_failed")
            raise

    def close(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._dry_run or self._client is None:
            return
        try:
            if self._connected:
                self._publish_raw(
                    f"{self._settings.mqtt_topic_prefix}/availability",
                    "offline",
                    retain=True,
                )
        except Exception:
            logger.warning("mqtt_offline_publish_failed")
        finally:
            self._connected = False
            if self._loop_started:
                self._client.loop_stop()
                self._loop_started = False
            try:
                self._client.disconnect()
            except Exception:
                logger.warning("mqtt_disconnect_failed")

    def publish_price_observation(
        self,
        *,
        team: TeamInfo,
        game: ScheduledGame,
        observation: PriceObservation,
        state_store: StateStore,
        state: TrackerState,
    ) -> str:
        """Publish one price observation and return its dynamic entity ID."""
        descriptor = build_price_entity_descriptor(
            settings=self._settings,
            team=team,
            game=game,
            source=observation.source,
            currency=observation.currency,
        )
        state_value = (
            f"{observation.cheapest_price:.2f}"
            if observation.cheapest_price is not None
            else "unknown"
        )
        attributes_payload = {
            "game_id": observation.game_id,
            "game_pk": game.game_pk,
            "game_date": game.official_date,
            "game_datetime": observation.game_datetime.isoformat(),
            "matchup": f"{observation.away_team} at {observation.home_team}",
            "home_team": observation.home_team,
            "away_team": observation.away_team,
            "opponent": observation.away_team,
            "venue": observation.venue,
            "source": observation.source,
            "source_display_name": observation.source.title(),
            "source_status": observation.source_status.value,
            "source_url": observation.source_url,
            "source_event_id": observation.source_event_id,
            "currency": observation.currency,
            "price_is_all_in": observation.price_is_all_in,
            "notes": observation.notes,
        }
        self._publish_entity(
            descriptor=descriptor,
            state_value=state_value,
            attributes_payload=attributes_payload,
            state_store=state_store,
            state=state,
            dynamic=True,
        )
        return descriptor.unique_id

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
        """Publish a provider health sensor."""
        descriptor = build_static_sensor_descriptor(
            settings=self._settings,
            team=team,
            sensor_key=f"{capability.source}_health",
            name=f"{capability.source.title()} Provider Health",
            state_topic_suffix=f"providers/{capability.source}/health",
            icon="mdi:heart-pulse",
            attributes=True,
            device_class="enum",
            entity_category="diagnostic",
            options=["healthy", "backoff", "error", "unconfigured"],
        )
        if not configured:
            state_value = "unconfigured"
        elif healthy:
            state_value = "healthy"
        elif health.backoff_until is not None:
            state_value = "backoff"
        else:
            state_value = "error"

        attributes_payload = {
            "source": capability.source,
            "support_level": capability.source_status.value,
            "auth_required": capability.auth_required,
            "implemented_fields": list(capability.implemented_fields),
            "limitations": list(capability.limitations),
            "consecutive_failures": health.consecutive_failures,
            "last_successful_poll_at": _dt_to_str(health.last_successful_poll_at),
            "last_error_at": _dt_to_str(health.last_error_at),
            "last_error": (
                redact_sensitive_text(health.last_error) if health.last_error is not None else None
            ),
            "backoff_until": _dt_to_str(health.backoff_until),
        }
        self._publish_entity(
            descriptor=descriptor,
            state_value=state_value,
            attributes_payload=attributes_payload,
            state_store=state_store,
            state=state,
            dynamic=False,
        )

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
        """Publish service-level sensors for operations and dashboards."""
        count_descriptor = build_static_sensor_descriptor(
            settings=self._settings,
            team=team,
            sensor_key="tracked_home_games",
            name="Tracked Home Games",
            state_topic_suffix="service/tracked_home_games",
            icon="mdi:baseball-diamond",
            entity_category="diagnostic",
        )
        next_poll_descriptor = build_static_sensor_descriptor(
            settings=self._settings,
            team=team,
            sensor_key="next_poll",
            name="Next Poll",
            state_topic_suffix="service/next_poll",
            icon="mdi:clock-outline",
            device_class="timestamp",
            entity_category="diagnostic",
        )
        last_completed_descriptor = build_static_sensor_descriptor(
            settings=self._settings,
            team=team,
            sensor_key="last_completed_poll",
            name="Last Completed Poll",
            state_topic_suffix="service/last_completed_poll",
            icon="mdi:clock-check-outline",
            device_class="timestamp",
            entity_category="diagnostic",
        )

        self._publish_entity(
            descriptor=count_descriptor,
            state_value=str(tracked_games),
            attributes_payload=None,
            state_store=state_store,
            state=state,
            dynamic=False,
        )
        self._publish_entity(
            descriptor=next_poll_descriptor,
            state_value=next_poll_at.isoformat(),
            attributes_payload=None,
            state_store=state_store,
            state=state,
            dynamic=False,
        )
        self._publish_entity(
            descriptor=last_completed_descriptor,
            state_value=last_completed_poll_at.isoformat() if last_completed_poll_at else "unknown",
            attributes_payload=None,
            state_store=state_store,
            state=state,
            dynamic=False,
        )

    def cleanup_stale_dynamic_entities(
        self,
        *,
        active_unique_ids: set[str],
        state_store: StateStore,
        state: TrackerState,
    ) -> None:
        """Delete Home Assistant discovery payloads for stale game entities."""
        if self._dry_run:
            return
        stale_ids = set(state.dynamic_entities) - active_unique_ids
        for unique_id in stale_ids:
            discovery_topic = state.dynamic_entities[unique_id]
            self._publish_raw(discovery_topic, "", retain=True)
            state_store.clear_published_topic(state, topic=discovery_topic)
            state_store.unregister_entity(state, unique_id=unique_id)
            logger.info("removed_stale_entity", unique_id=unique_id)

    def _publish_entity(
        self,
        *,
        descriptor: EntityDescriptor,
        state_value: str,
        attributes_payload: Mapping[str, object] | None,
        state_store: StateStore,
        state: TrackerState,
        dynamic: bool,
    ) -> None:
        config_json = json.dumps(descriptor.config_payload, sort_keys=True)
        if self._dry_run:
            logger.info(
                "dry_run_publish_entity",
                unique_id=descriptor.unique_id,
                state_value=state_value,
            )
            return

        self._publish_if_changed(
            topic=descriptor.discovery_topic,
            payload=config_json,
            state_store=state_store,
            state=state,
        )
        self._publish_if_changed(
            topic=descriptor.state_topic,
            payload=state_value,
            state_store=state_store,
            state=state,
        )
        if descriptor.attributes_topic and attributes_payload is not None:
            attributes_json = json.dumps(attributes_payload, sort_keys=True)
            self._publish_if_changed(
                topic=descriptor.attributes_topic,
                payload=attributes_json,
                state_store=state_store,
                state=state,
            )
        if dynamic:
            state_store.register_entity(
                state,
                unique_id=descriptor.unique_id,
                discovery_topic=descriptor.discovery_topic,
            )

    def _publish_if_changed(
        self,
        *,
        topic: str,
        payload: str,
        state_store: StateStore,
        state: TrackerState,
    ) -> None:
        if state.published_topics.get(topic) == payload:
            return
        self._publish_raw(topic, payload, retain=True)
        state_store.track_published_topic(state, topic=topic, payload=payload)

    def _publish_raw(self, topic: str, payload: str, *, retain: bool) -> None:
        if self._dry_run:
            logger.info("dry_run_publish", topic=topic, payload=payload, retain=retain)
            return
        if self._client is None:
            msg = "MQTT client is not configured"
            raise RuntimeError(msg)
        try:
            message_info = self._client.publish(topic, payload=payload, qos=1, retain=retain)
            message_info.wait_for_publish()
        except Exception as exc:
            self._connected = False
            logger.error(
                "mqtt_publish_failed",
                topic=topic,
                retain=retain,
                error=redact_sensitive_text(str(exc)),
                error_type=type(exc).__name__,
            )
            raise
        if message_info.rc != mqtt.MQTT_ERR_SUCCESS:
            self._connected = False
            msg = f"MQTT publish failed with rc={message_info.rc}"
            logger.error("mqtt_publish_failed_rc", topic=topic, retain=retain, rc=message_info.rc)
            raise RuntimeError(msg)


def _dt_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
