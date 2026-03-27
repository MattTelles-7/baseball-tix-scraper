"""MLB schedule client and home-game filtering."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from mlb_ticket_tracker.models import ScheduledGame, TeamInfo


class MlbScheduleClient:
    """Client for the public MLB schedule endpoint."""

    def __init__(self, *, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch_upcoming_games(
        self,
        *,
        team: TeamInfo,
        lookahead_days: int,
        home_games_only: bool,
        timezone: str,
        grace_minutes: int = 0,
        now: datetime | None = None,
    ) -> list[ScheduledGame]:
        """Fetch and normalize upcoming MLB games for a team."""
        tzinfo = ZoneInfo(timezone)
        current_time = now.astimezone(tzinfo) if now else datetime.now(tz=tzinfo)
        earliest_allowed = current_time - timedelta(minutes=grace_minutes)
        end_time = current_time + timedelta(days=lookahead_days)

        response = httpx.get(
            "https://statsapi.mlb.com/api/v1/schedule",
            params={
                "sportId": "1",
                "teamId": str(team.id),
                "startDate": earliest_allowed.date().isoformat(),
                "endDate": end_time.date().isoformat(),
                "gameType": "R",
                "hydrate": "venue",
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        games: list[ScheduledGame] = []
        for day in payload.get("dates", []):
            for game in day.get("games", []):
                normalized_game = normalize_scheduled_game(game=game, timezone=timezone)
                if normalized_game.game_datetime + timedelta(minutes=grace_minutes) < current_time:
                    continue
                if home_games_only and normalized_game.home_team_id != team.id:
                    continue
                games.append(normalized_game)

        games.sort(key=lambda item: item.game_datetime)
        return games


def normalize_scheduled_game(*, game: dict[str, object], timezone: str) -> ScheduledGame:
    """Convert a raw MLB schedule game payload into a typed model."""
    teams = _require_mapping(game, "teams")
    home = _require_mapping(teams, "home")
    away = _require_mapping(teams, "away")
    home_team = _require_mapping(home, "team")
    away_team = _require_mapping(away, "team")
    venue = _require_mapping(game, "venue")
    status = _require_mapping(game, "status")

    game_datetime = datetime.fromisoformat(_require_string(game, "gameDate").replace("Z", "+00:00"))

    return ScheduledGame(
        game_id=f"mlb:{_require_int(game, 'gamePk')}",
        game_pk=_require_int(game, "gamePk"),
        game_datetime=game_datetime,
        official_date=_require_string(game, "officialDate"),
        home_team=_require_string(home_team, "name"),
        away_team=_require_string(away_team, "name"),
        venue=_require_string(venue, "name"),
        timezone=timezone,
        home_team_id=_require_int(home_team, "id"),
        away_team_id=_require_int(away_team, "id"),
        game_type=_require_string(game, "gameType"),
        status=_require_string(status, "detailedState"),
    )


def _require_mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        msg = f"expected object for {key}"
        raise ValueError(msg)
    return value


def _require_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        msg = f"expected string for {key}"
        raise ValueError(msg)
    return value


def _require_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        msg = f"expected integer for {key}"
        raise ValueError(msg)
    return value
