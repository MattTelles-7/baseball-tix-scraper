from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mlb_ticket_tracker.config import Settings, TicketmasterSettings
from mlb_ticket_tracker.models import (
    MatchedEvent,
    PriceObservation,
    ScheduledGame,
    SourceStatus,
    TeamInfo,
)


@pytest.fixture
def settings_factory(tmp_path: Path) -> Callable[..., Settings]:
    def factory(**overrides: object) -> Settings:
        payload: dict[str, object] = {
            "TEAM_ID": 113,
            "MQTT_HOST": "mqtt.local",
            "MQTT_PORT": 1883,
            "MQTT_TOPIC_PREFIX": "mlb_ticket_tracker",
            "MQTT_DISCOVERY_PREFIX": "homeassistant",
            "MQTT_CLIENT_ID": "mlb-ticket-tracker-test",
            "POLL_INTERVAL_MINUTES": 15,
            "POST_GAME_GRACE_MINUTES": 240,
            "DATA_DIR": str(tmp_path),
        }
        payload.update(overrides)
        return Settings.model_validate(payload)

    return factory


@pytest.fixture
def reds_team() -> TeamInfo:
    return TeamInfo(
        id=113,
        slug="cincinnati-reds",
        name="Cincinnati Reds",
        city="Cincinnati",
        venue="Great American Ball Park",
        aliases=("reds",),
    )


@pytest.fixture
def scheduled_game_factory() -> Callable[..., ScheduledGame]:
    def factory(**overrides: object) -> ScheduledGame:
        payload: dict[str, object] = {
            "game_id": "mlb:824540",
            "game_pk": 824540,
            "game_datetime": datetime(2026, 3, 28, 20, 10, tzinfo=UTC),
            "official_date": "2026-03-28",
            "home_team": "Cincinnati Reds",
            "away_team": "Boston Red Sox",
            "venue": "Great American Ball Park",
            "timezone": "America/New_York",
            "home_team_id": 113,
            "away_team_id": 111,
            "game_type": "R",
            "status": "Scheduled",
        }
        payload.update(overrides)
        return ScheduledGame.model_validate(payload)

    return factory


@pytest.fixture
def home_game(scheduled_game_factory: Callable[..., ScheduledGame]) -> ScheduledGame:
    return scheduled_game_factory()


@pytest.fixture
def matched_event(home_game: ScheduledGame) -> MatchedEvent:
    return MatchedEvent(
        source="ticketmaster",
        game_id=home_game.game_id,
        source_event_id="G5v123",
        source_url="https://ticketmaster.test/event",
        matched_at=datetime(2026, 3, 27, tzinfo=UTC),
    )


@pytest.fixture
def price_observation(home_game: ScheduledGame, matched_event: MatchedEvent) -> PriceObservation:
    return PriceObservation(
        source="ticketmaster",
        source_status=SourceStatus.SUPPORTED,
        game_id=home_game.game_id,
        game_datetime=home_game.game_datetime,
        home_team=home_game.home_team,
        away_team=home_game.away_team,
        venue=home_game.venue,
        currency="USD",
        cheapest_price=24.5,
        price_is_all_in=False,
        source_event_id=matched_event.source_event_id,
        source_url=matched_event.source_url,
        checked_at=datetime(2026, 3, 27, tzinfo=UTC),
        notes="Uses Discovery API minimum price.",
    )


@pytest.fixture
def schedule_game_payload_factory() -> Callable[..., dict[str, object]]:
    def factory(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "gamePk": 824540,
            "gameType": "R",
            "gameDate": "2026-03-28T20:10:00Z",
            "officialDate": "2026-03-28",
            "status": {"detailedState": "Scheduled"},
            "teams": {
                "away": {"team": {"id": 111, "name": "Boston Red Sox"}},
                "home": {"team": {"id": 113, "name": "Cincinnati Reds"}},
            },
            "venue": {"name": "Great American Ball Park"},
        }
        payload.update(overrides)
        return payload

    return factory


@pytest.fixture
def schedule_payload_factory() -> Callable[[list[dict[str, object]]], dict[str, object]]:
    def factory(games: list[dict[str, object]]) -> dict[str, object]:
        return {"dates": [{"games": games}]}

    return factory


@pytest.fixture
def ticketmaster_search_payload_factory() -> Callable[[list[dict[str, object]]], dict[str, object]]:
    def factory(events: list[dict[str, object]]) -> dict[str, object]:
        return {"_embedded": {"events": events}}

    return factory


@pytest.fixture
def ticketmaster_event_factory() -> Callable[..., dict[str, object]]:
    def factory(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": "G5v123",
            "name": "Boston Red Sox at Cincinnati Reds",
            "url": "https://ticketmaster.test/event",
            "dates": {"start": {"localDate": "2026-03-28"}},
            "_embedded": {"venues": [{"name": "Great American Ball Park"}]},
        }
        payload.update(overrides)
        return payload

    return factory


@pytest.fixture
def ticketmaster_detail_payload_factory() -> Callable[..., dict[str, object]]:
    def factory(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": "G5v123",
            "url": "https://ticketmaster.test/event",
            "priceRanges": [
                {
                    "type": "standard",
                    "currency": "USD",
                    "min": 24.5,
                    "max": 125.0,
                }
            ],
        }
        payload.update(overrides)
        return payload

    return factory


@pytest.fixture
def ticketmaster_settings() -> TicketmasterSettings:
    return TicketmasterSettings(enabled=True, rate_limit_delay_seconds=0.0, api_key="key")
