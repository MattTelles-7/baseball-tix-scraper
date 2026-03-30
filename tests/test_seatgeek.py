from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from pytest_httpx import HTTPXMock

from mlb_ticket_tracker.config import SeatGeekSettings
from mlb_ticket_tracker.models import MatchedEvent, ScheduledGame, SourceStatus
from mlb_ticket_tracker.providers.seatgeek import SeatGeekProvider


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


def test_seatgeek_match_events(
    httpx_mock: HTTPXMock,
    seatgeek_settings: SeatGeekSettings,
    seatgeek_events_payload_factory: Callable[[list[dict[str, object]]], dict[str, object]],
    seatgeek_event_factory: Callable[..., dict[str, object]],
) -> None:
    provider = SeatGeekProvider(settings=seatgeek_settings, timeout_seconds=5)
    httpx_mock.add_response(json=seatgeek_events_payload_factory([seatgeek_event_factory()]))

    matches = provider.match_events([_game()], {})

    matched = matches["seatgeek:mlb:824540"]
    assert matched.source_event_id == "987654"
    assert (
        matched.source_url
        == "https://seatgeek.com/red-sox-at-reds-tickets/cincinnati-ohio-great-american-ball-park-2026-03-28/sports/987654"
    )


def test_seatgeek_match_events_falls_back_to_home_team_search(
    httpx_mock: HTTPXMock,
    seatgeek_settings: SeatGeekSettings,
    seatgeek_events_payload_factory: Callable[[list[dict[str, object]]], dict[str, object]],
    seatgeek_event_factory: Callable[..., dict[str, object]],
) -> None:
    provider = SeatGeekProvider(settings=seatgeek_settings, timeout_seconds=5)
    httpx_mock.add_response(json=seatgeek_events_payload_factory([]))
    httpx_mock.add_response(json=seatgeek_events_payload_factory([seatgeek_event_factory()]))

    matches = provider.match_events([_game()], {})

    assert matches["seatgeek:mlb:824540"].source_event_id == "987654"


def test_seatgeek_fetch_lowest_price(
    httpx_mock: HTTPXMock,
    seatgeek_settings: SeatGeekSettings,
    seatgeek_event_factory: Callable[..., dict[str, object]],
) -> None:
    provider = SeatGeekProvider(settings=seatgeek_settings, timeout_seconds=5)
    httpx_mock.add_response(json=seatgeek_event_factory())

    observation = provider.fetch_lowest_price(
        _game(),
        MatchedEvent(
            source="seatgeek",
            game_id="mlb:824540",
            source_event_id="987654",
            source_url="https://seatgeek.com/example-event",
            matched_at=datetime(2026, 3, 27, tzinfo=UTC),
        ),
    )

    assert observation.source_status is SourceStatus.PARTIAL
    assert observation.cheapest_price == 31.0
    assert observation.currency == "USD"
    assert observation.price_is_all_in is None


def test_seatgeek_fetch_without_public_lowest_price_returns_unavailable(
    httpx_mock: HTTPXMock,
    home_game: ScheduledGame,
    seatgeek_settings: SeatGeekSettings,
    seatgeek_event_factory: Callable[..., dict[str, object]],
) -> None:
    provider = SeatGeekProvider(settings=seatgeek_settings, timeout_seconds=5)
    httpx_mock.add_response(
        json=seatgeek_event_factory(
            stats={"listing_count": 0, "lowest_price": None, "highest_price": None}
        )
    )

    observation = provider.fetch_lowest_price(
        home_game,
        MatchedEvent(
            source="seatgeek",
            game_id=home_game.game_id,
            source_event_id="987654",
            source_url="https://seatgeek.com/example-event",
            matched_at=datetime(2026, 3, 27, tzinfo=UTC),
        ),
    )

    assert observation.source_status is SourceStatus.UNAVAILABLE
    assert observation.cheapest_price is None
    assert (
        observation.notes
        == "SeatGeek event found, but no public lowest price is currently available."
    )


def test_seatgeek_match_events_uses_cached_match(
    httpx_mock: HTTPXMock,
    home_game: ScheduledGame,
    seatgeek_settings: SeatGeekSettings,
) -> None:
    provider = SeatGeekProvider(settings=seatgeek_settings, timeout_seconds=5)
    matched_event = MatchedEvent(
        source="seatgeek",
        game_id=home_game.game_id,
        source_event_id="987654",
        source_url="https://seatgeek.com/example-event",
        matched_at=datetime(2026, 3, 27, tzinfo=UTC),
    )

    matches = provider.match_events(
        [home_game],
        {"seatgeek:mlb:824540": matched_event},
    )

    assert matches["seatgeek:mlb:824540"] == matched_event
    assert httpx_mock.get_requests() == []


def test_seatgeek_fetch_without_match(
    seatgeek_settings: SeatGeekSettings,
) -> None:
    provider = SeatGeekProvider(settings=seatgeek_settings, timeout_seconds=5)

    observation = provider.fetch_lowest_price(_game(), None)

    assert observation.source_status is SourceStatus.UNAVAILABLE
    assert observation.cheapest_price is None


def test_seatgeek_healthcheck_requires_client_id() -> None:
    provider = SeatGeekProvider(
        settings=SeatGeekSettings(enabled=True, rate_limit_delay_seconds=0.0, client_id=None),
        timeout_seconds=5,
    )

    assert provider.healthcheck() is False
