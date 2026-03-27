from __future__ import annotations

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
