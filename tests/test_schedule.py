from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pytest_httpx import HTTPXMock

from mlb_ticket_tracker.models import TeamInfo
from mlb_ticket_tracker.schedule import MlbScheduleClient, normalize_scheduled_game
from mlb_ticket_tracker.teams import resolve_team


def test_resolve_team_by_slug() -> None:
    team = resolve_team(None, "cincinnati-reds", None)

    assert team.id == 113
    assert team.name == "Cincinnati Reds"


def test_resolve_team_by_alias_name() -> None:
    team = resolve_team(None, None, "reds")

    assert team.id == 113


def test_normalize_scheduled_game() -> None:
    game = {
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

    normalized = normalize_scheduled_game(game=game, timezone="America/New_York")

    assert normalized.game_id == "mlb:824540"
    assert normalized.home_team == "Cincinnati Reds"
    assert normalized.away_team == "Boston Red Sox"
    assert normalized.venue == "Great American Ball Park"


def test_fetch_upcoming_games_filters_home_games(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        json={
            "dates": [
                {
                    "games": [
                        {
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
                        },
                        {
                            "gamePk": 824541,
                            "gameType": "R",
                            "gameDate": "2026-03-29T20:10:00Z",
                            "officialDate": "2026-03-29",
                            "status": {"detailedState": "Scheduled"},
                            "teams": {
                                "away": {"team": {"id": 113, "name": "Cincinnati Reds"}},
                                "home": {"team": {"id": 111, "name": "Boston Red Sox"}},
                            },
                            "venue": {"name": "Fenway Park"},
                        },
                    ]
                }
            ]
        }
    )
    client = MlbScheduleClient(timeout_seconds=5)
    team = resolve_team(113, None, None)

    games = client.fetch_upcoming_games(
        team=team,
        lookahead_days=30,
        home_games_only=True,
        timezone="America/New_York",
        grace_minutes=0,
        now=datetime(2026, 3, 27, tzinfo=UTC),
    )

    assert [game.game_pk for game in games] == [824540]


def test_fetch_upcoming_games_keeps_recent_game_in_grace_window(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        json={
            "dates": [
                {
                    "games": [
                        {
                            "gamePk": 824540,
                            "gameType": "R",
                            "gameDate": "2026-03-28T20:10:00Z",
                            "officialDate": "2026-03-28",
                            "status": {"detailedState": "In Progress"},
                            "teams": {
                                "away": {"team": {"id": 111, "name": "Boston Red Sox"}},
                                "home": {"team": {"id": 113, "name": "Cincinnati Reds"}},
                            },
                            "venue": {"name": "Great American Ball Park"},
                        }
                    ]
                }
            ]
        }
    )
    client = MlbScheduleClient(timeout_seconds=5)
    team = resolve_team(113, None, None)

    games = client.fetch_upcoming_games(
        team=team,
        lookahead_days=30,
        home_games_only=True,
        timezone="America/New_York",
        grace_minutes=240,
        now=datetime(2026, 3, 28, 22, 0, tzinfo=UTC),
    )

    assert [game.game_pk for game in games] == [824540]


def test_normalize_scheduled_game_rejects_invalid_payload(
    schedule_game_payload_factory: Callable[..., dict[str, object]],
) -> None:
    game = schedule_game_payload_factory(venue=None)

    with pytest.raises(ValueError, match="expected object for venue"):
        normalize_scheduled_game(game=game, timezone="America/New_York")


def test_fetch_upcoming_games_excludes_games_past_grace_window(
    httpx_mock: HTTPXMock,
    schedule_game_payload_factory: Callable[..., dict[str, object]],
    schedule_payload_factory: Callable[[list[dict[str, object]]], dict[str, object]],
) -> None:
    httpx_mock.add_response(
        json=schedule_payload_factory([schedule_game_payload_factory()]),
    )
    client = MlbScheduleClient(timeout_seconds=5)
    team = resolve_team(113, None, None)

    games = client.fetch_upcoming_games(
        team=team,
        lookahead_days=30,
        home_games_only=True,
        timezone="America/New_York",
        grace_minutes=240,
        now=datetime(2026, 3, 29, 5, 0, tzinfo=UTC),
    )

    assert games == []


def test_fetch_upcoming_games_sorts_games_and_can_include_away_games(
    httpx_mock: HTTPXMock,
    schedule_game_payload_factory: Callable[..., dict[str, object]],
    schedule_payload_factory: Callable[[list[dict[str, object]]], dict[str, object]],
) -> None:
    later_home_game = schedule_game_payload_factory(
        gamePk=824541,
        gameDate="2026-03-30T20:10:00Z",
        officialDate="2026-03-30",
    )
    earlier_away_game = schedule_game_payload_factory(
        gamePk=824539,
        gameDate="2026-03-29T17:10:00Z",
        officialDate="2026-03-29",
        teams={
            "away": {"team": {"id": 113, "name": "Cincinnati Reds"}},
            "home": {"team": {"id": 112, "name": "Chicago Cubs"}},
        },
        venue={"name": "Wrigley Field"},
    )
    httpx_mock.add_response(
        json=schedule_payload_factory([later_home_game, earlier_away_game]),
    )
    client = MlbScheduleClient(timeout_seconds=5)
    team = resolve_team(113, None, None)

    games = client.fetch_upcoming_games(
        team=team,
        lookahead_days=30,
        home_games_only=False,
        timezone="America/New_York",
        grace_minutes=0,
        now=datetime(2026, 3, 27, tzinfo=UTC),
    )

    assert [game.game_pk for game in games] == [824539, 824541]


def test_fetch_upcoming_games_uses_expected_schedule_query_parameters(
    httpx_mock: HTTPXMock,
    reds_team: TeamInfo,
    schedule_payload_factory: Callable[[list[dict[str, object]]], dict[str, object]],
) -> None:
    httpx_mock.add_response(json=schedule_payload_factory([]))
    client = MlbScheduleClient(timeout_seconds=5)
    now = datetime(2026, 3, 29, 1, 30, tzinfo=UTC)

    client.fetch_upcoming_games(
        team=reds_team,
        lookahead_days=45,
        home_games_only=True,
        timezone="America/New_York",
        grace_minutes=240,
        now=now,
    )

    request = httpx_mock.get_requests()[0]
    current_time = now.astimezone(ZoneInfo("America/New_York"))
    earliest_allowed = current_time - timedelta(minutes=240)
    end_time = current_time + timedelta(days=45)

    assert request.url.host == "statsapi.mlb.com"
    assert request.url.path == "/api/v1/schedule"
    assert request.url.params["sportId"] == "1"
    assert request.url.params["teamId"] == "113"
    assert request.url.params["gameType"] == "R"
    assert request.url.params["hydrate"] == "venue"
    assert request.url.params["startDate"] == earliest_allowed.date().isoformat()
    assert request.url.params["endDate"] == end_time.date().isoformat()
