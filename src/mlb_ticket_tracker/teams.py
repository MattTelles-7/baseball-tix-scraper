"""Static MLB team catalog and resolution helpers."""

from __future__ import annotations

from collections.abc import Iterable

from mlb_ticket_tracker.models import TeamInfo

TEAM_CATALOG: tuple[TeamInfo, ...] = (
    TeamInfo(
        id=108,
        slug="los-angeles-angels",
        name="Los Angeles Angels",
        city="Anaheim",
        venue="Angel Stadium",
        aliases=("angels",),
    ),
    TeamInfo(
        id=109,
        slug="arizona-diamondbacks",
        name="Arizona Diamondbacks",
        city="Phoenix",
        venue="Chase Field",
        aliases=("diamondbacks", "d-backs"),
    ),
    TeamInfo(
        id=110,
        slug="baltimore-orioles",
        name="Baltimore Orioles",
        city="Baltimore",
        venue="Oriole Park at Camden Yards",
        aliases=("orioles",),
    ),
    TeamInfo(
        id=111,
        slug="boston-red-sox",
        name="Boston Red Sox",
        city="Boston",
        venue="Fenway Park",
        aliases=("red sox",),
    ),
    TeamInfo(
        id=112,
        slug="chicago-cubs",
        name="Chicago Cubs",
        city="Chicago",
        venue="Wrigley Field",
        aliases=("cubs",),
    ),
    TeamInfo(
        id=113,
        slug="cincinnati-reds",
        name="Cincinnati Reds",
        city="Cincinnati",
        venue="Great American Ball Park",
        aliases=("reds",),
    ),
    TeamInfo(
        id=114,
        slug="cleveland-guardians",
        name="Cleveland Guardians",
        city="Cleveland",
        venue="Progressive Field",
        aliases=("guardians",),
    ),
    TeamInfo(
        id=115,
        slug="colorado-rockies",
        name="Colorado Rockies",
        city="Denver",
        venue="Coors Field",
        aliases=("rockies",),
    ),
    TeamInfo(
        id=116,
        slug="detroit-tigers",
        name="Detroit Tigers",
        city="Detroit",
        venue="Comerica Park",
        aliases=("tigers",),
    ),
    TeamInfo(
        id=117,
        slug="houston-astros",
        name="Houston Astros",
        city="Houston",
        venue="Daikin Park",
        aliases=("astros",),
    ),
    TeamInfo(
        id=118,
        slug="kansas-city-royals",
        name="Kansas City Royals",
        city="Kansas City",
        venue="Kauffman Stadium",
        aliases=("royals",),
    ),
    TeamInfo(
        id=119,
        slug="los-angeles-dodgers",
        name="Los Angeles Dodgers",
        city="Los Angeles",
        venue="Dodger Stadium",
        aliases=("dodgers",),
    ),
    TeamInfo(
        id=120,
        slug="washington-nationals",
        name="Washington Nationals",
        city="Washington",
        venue="Nationals Park",
        aliases=("nationals",),
    ),
    TeamInfo(
        id=121,
        slug="new-york-mets",
        name="New York Mets",
        city="New York",
        venue="Citi Field",
        aliases=("mets",),
    ),
    TeamInfo(
        id=133,
        slug="oakland-athletics",
        name="Athletics",
        city="West Sacramento",
        venue="Sutter Health Park",
        aliases=("athletics", "oakland athletics", "a's"),
    ),
    TeamInfo(
        id=134,
        slug="pittsburgh-pirates",
        name="Pittsburgh Pirates",
        city="Pittsburgh",
        venue="PNC Park",
        aliases=("pirates",),
    ),
    TeamInfo(
        id=135,
        slug="san-diego-padres",
        name="San Diego Padres",
        city="San Diego",
        venue="Petco Park",
        aliases=("padres",),
    ),
    TeamInfo(
        id=136,
        slug="seattle-mariners",
        name="Seattle Mariners",
        city="Seattle",
        venue="T-Mobile Park",
        aliases=("mariners",),
    ),
    TeamInfo(
        id=137,
        slug="san-francisco-giants",
        name="San Francisco Giants",
        city="San Francisco",
        venue="Oracle Park",
        aliases=("giants",),
    ),
    TeamInfo(
        id=138,
        slug="st-louis-cardinals",
        name="St. Louis Cardinals",
        city="St. Louis",
        venue="Busch Stadium",
        aliases=("cardinals",),
    ),
    TeamInfo(
        id=139,
        slug="tampa-bay-rays",
        name="Tampa Bay Rays",
        city="St. Petersburg",
        venue="George M. Steinbrenner Field",
        aliases=("rays",),
    ),
    TeamInfo(
        id=140,
        slug="texas-rangers",
        name="Texas Rangers",
        city="Arlington",
        venue="Globe Life Field",
        aliases=("rangers",),
    ),
    TeamInfo(
        id=141,
        slug="toronto-blue-jays",
        name="Toronto Blue Jays",
        city="Toronto",
        venue="Rogers Centre",
        aliases=("blue jays",),
    ),
    TeamInfo(
        id=142,
        slug="minnesota-twins",
        name="Minnesota Twins",
        city="Minneapolis",
        venue="Target Field",
        aliases=("twins",),
    ),
    TeamInfo(
        id=143,
        slug="philadelphia-phillies",
        name="Philadelphia Phillies",
        city="Philadelphia",
        venue="Citizens Bank Park",
        aliases=("phillies",),
    ),
    TeamInfo(
        id=144,
        slug="atlanta-braves",
        name="Atlanta Braves",
        city="Atlanta",
        venue="Truist Park",
        aliases=("braves",),
    ),
    TeamInfo(
        id=145,
        slug="chicago-white-sox",
        name="Chicago White Sox",
        city="Chicago",
        venue="Rate Field",
        aliases=("white sox",),
    ),
    TeamInfo(
        id=146,
        slug="miami-marlins",
        name="Miami Marlins",
        city="Miami",
        venue="loanDepot park",
        aliases=("marlins",),
    ),
    TeamInfo(
        id=147,
        slug="new-york-yankees",
        name="New York Yankees",
        city="Bronx",
        venue="Yankee Stadium",
        aliases=("yankees",),
    ),
    TeamInfo(
        id=158,
        slug="milwaukee-brewers",
        name="Milwaukee Brewers",
        city="Milwaukee",
        venue="American Family Field",
        aliases=("brewers",),
    ),
)

_BY_ID = {team.id: team for team in TEAM_CATALOG}


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("-", " ").split())


def _candidate_names(team: TeamInfo) -> Iterable[str]:
    yield team.slug
    yield team.name
    yield team.city
    yield from team.aliases


def resolve_team(team_id: int | None, team_slug: str | None, team_name: str | None) -> TeamInfo:
    """Resolve a configured team from ID, slug, or name."""
    if team_id is not None:
        team = _BY_ID.get(team_id)
        if team is None:
            msg = f"unknown TEAM_ID: {team_id}"
            raise ValueError(msg)
        return team

    if team_slug:
        normalized_slug = _normalize(team_slug)
        for team in TEAM_CATALOG:
            if _normalize(team.slug) == normalized_slug:
                return team

    if team_name:
        normalized_name = _normalize(team_name)
        for team in TEAM_CATALOG:
            if normalized_name in {_normalize(value) for value in _candidate_names(team)}:
                return team

    msg = "configure TEAM_ID, TEAM_SLUG, or TEAM_NAME"
    raise ValueError(msg)
