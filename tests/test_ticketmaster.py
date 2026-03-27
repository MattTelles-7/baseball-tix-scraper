from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from pytest_httpx import HTTPXMock

from mlb_ticket_tracker.config import TicketmasterSettings
from mlb_ticket_tracker.models import MatchedEvent, ScheduledGame, SourceStatus
from mlb_ticket_tracker.providers.ticketmaster import TicketmasterProvider


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


def test_ticketmaster_match_events(httpx_mock: HTTPXMock) -> None:
    provider = TicketmasterProvider(
        settings=TicketmasterSettings(enabled=True, rate_limit_delay_seconds=0.0, api_key="key"),
        timeout_seconds=5,
    )
    httpx_mock.add_response(
        json={
            "_embedded": {
                "events": [
                    {
                        "id": "G5v123",
                        "name": "Boston Red Sox at Cincinnati Reds",
                        "url": "https://ticketmaster.test/event",
                        "dates": {"start": {"localDate": "2026-03-28"}},
                        "_embedded": {"venues": [{"name": "Great American Ball Park"}]},
                    }
                ]
            }
        }
    )

    matches = provider.match_events([_game()], {})

    assert matches["ticketmaster:mlb:824540"].source_event_id == "G5v123"


def test_ticketmaster_fetch_lowest_price(httpx_mock: HTTPXMock) -> None:
    provider = TicketmasterProvider(
        settings=TicketmasterSettings(enabled=True, rate_limit_delay_seconds=0.0, api_key="key"),
        timeout_seconds=5,
    )
    httpx_mock.add_response(
        json={
            "id": "G5v123",
            "url": "https://ticketmaster.test/event",
            "priceRanges": [{"type": "standard", "currency": "USD", "min": 24.5, "max": 125.0}],
        }
    )

    observation = provider.fetch_lowest_price(
        _game(),
        MatchedEvent(
            source="ticketmaster",
            game_id="mlb:824540",
            source_event_id="G5v123",
            source_url="https://ticketmaster.test/event",
            matched_at=datetime(2026, 3, 27, tzinfo=UTC),
        ),
    )

    assert observation.source_status is SourceStatus.SUPPORTED
    assert observation.cheapest_price == 24.5


def test_ticketmaster_fetch_without_match() -> None:
    provider = TicketmasterProvider(
        settings=TicketmasterSettings(enabled=True, rate_limit_delay_seconds=0.0, api_key="key"),
        timeout_seconds=5,
    )

    observation = provider.fetch_lowest_price(_game(), None)

    assert observation.source_status is SourceStatus.UNAVAILABLE
    assert observation.cheapest_price is None


def test_ticketmaster_match_events_uses_cached_match(
    httpx_mock: HTTPXMock,
    home_game: ScheduledGame,
    matched_event: MatchedEvent,
    ticketmaster_settings: TicketmasterSettings,
) -> None:
    provider = TicketmasterProvider(settings=ticketmaster_settings, timeout_seconds=5)

    matches = provider.match_events(
        [home_game],
        {"ticketmaster:mlb:824540": matched_event},
    )

    assert matches["ticketmaster:mlb:824540"] == matched_event
    assert httpx_mock.get_requests() == []


def test_ticketmaster_match_events_selects_best_scored_candidate(
    httpx_mock: HTTPXMock,
    home_game: ScheduledGame,
    ticketmaster_settings: TicketmasterSettings,
    ticketmaster_search_payload_factory: Callable[[list[dict[str, object]]], dict[str, object]],
    ticketmaster_event_factory: Callable[..., dict[str, object]],
) -> None:
    provider = TicketmasterProvider(settings=ticketmaster_settings, timeout_seconds=5)
    httpx_mock.add_response(
        json=ticketmaster_search_payload_factory(
            [
                ticketmaster_event_factory(
                    id="partial-match",
                    name="Red Sox at Reds",
                    _embedded={"venues": [{"name": "Day Air Ballpark"}]},
                ),
                ticketmaster_event_factory(id="best-match"),
            ]
        )
    )

    matches = provider.match_events([home_game], {})

    assert matches["ticketmaster:mlb:824540"].source_event_id == "best-match"


def test_ticketmaster_fetch_without_public_minimum_returns_unavailable(
    httpx_mock: HTTPXMock,
    home_game: ScheduledGame,
    matched_event: MatchedEvent,
    ticketmaster_settings: TicketmasterSettings,
    ticketmaster_detail_payload_factory: Callable[..., dict[str, object]],
) -> None:
    provider = TicketmasterProvider(settings=ticketmaster_settings, timeout_seconds=5)
    httpx_mock.add_response(
        json=ticketmaster_detail_payload_factory(
            priceRanges=[{"type": "standard", "currency": "USD"}],
        )
    )

    observation = provider.fetch_lowest_price(home_game, matched_event)

    assert observation.source_status is SourceStatus.UNAVAILABLE
    assert observation.cheapest_price is None
    assert observation.currency == "USD"
    assert observation.notes == "Ticketmaster returned price ranges without a minimum value."


def test_ticketmaster_healthcheck_requires_api_key() -> None:
    provider = TicketmasterProvider(
        settings=TicketmasterSettings(enabled=True, rate_limit_delay_seconds=0.0, api_key=None),
        timeout_seconds=5,
    )

    assert provider.healthcheck() is False
