from __future__ import annotations

from datetime import UTC, datetime

from pytest_httpx import HTTPXMock

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
        now=datetime(2026, 3, 27, tzinfo=UTC),
    )

    assert [game.game_pk for game in games] == [824540]
