"""SeatGeek provider using the official Platform API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Any

import httpx

from mlb_ticket_tracker.config import SeatGeekSettings
from mlb_ticket_tracker.models import (
    MatchedEvent,
    PriceObservation,
    ProviderCapability,
    ScheduledGame,
    SourceStatus,
)
from mlb_ticket_tracker.providers.base import Provider


class SeatGeekProvider(Provider):
    """Partial SeatGeek adapter backed by the official Platform API."""

    source = "seatgeek"

    def __init__(
        self,
        *,
        settings: SeatGeekSettings,
        timeout_seconds: float,
    ) -> None:
        self._settings = settings
        self._timeout_seconds = timeout_seconds

    def capability_report(self) -> ProviderCapability:
        return ProviderCapability(
            source=self.source,
            source_status=SourceStatus.PARTIAL,
            auth_required=True,
            implemented_fields=("stats.lowest_price", "event_url", "event_id"),
            limitations=(
                "Uses SeatGeek stats.lowest_price rather than a direct listing feed.",
                "The public SeatGeek API does not expose an all-in pricing flag.",
            ),
        )

    def healthcheck(self) -> bool:
        return bool(self._settings.client_id)

    def match_events(
        self,
        games: list[ScheduledGame],
        cached_matches: dict[str, MatchedEvent],
    ) -> dict[str, MatchedEvent]:
        matches: dict[str, MatchedEvent] = {}
        for game in games:
            cache_key = _match_key(self.source, game.game_id)
            cached_match = cached_matches.get(cache_key)
            if cached_match is not None:
                matches[cache_key] = cached_match
                continue
            matched = self._search_event(game)
            if matched is not None:
                matches[cache_key] = matched
        return matches

    def fetch_lowest_price(
        self,
        game: ScheduledGame,
        matched_event: MatchedEvent | None,
    ) -> PriceObservation:
        checked_at = datetime.now(tz=UTC)
        if matched_event is None:
            return PriceObservation(
                source=self.source,
                source_status=SourceStatus.UNAVAILABLE,
                game_id=game.game_id,
                game_datetime=game.game_datetime,
                home_team=game.home_team,
                away_team=game.away_team,
                venue=game.venue,
                checked_at=checked_at,
                notes="No SeatGeek event match found for this game.",
            )

        payload = self._get_event_details(matched_event.source_event_id)
        stats = payload.get("stats")
        if not isinstance(stats, dict):
            return PriceObservation(
                source=self.source,
                source_status=SourceStatus.UNAVAILABLE,
                game_id=game.game_id,
                game_datetime=game.game_datetime,
                home_team=game.home_team,
                away_team=game.away_team,
                venue=game.venue,
                source_event_id=matched_event.source_event_id,
                source_url=matched_event.source_url,
                checked_at=checked_at,
                notes="SeatGeek event found, but listing statistics are currently unavailable.",
            )

        lowest_price = stats.get("lowest_price")
        if not isinstance(lowest_price, (int, float)):
            return PriceObservation(
                source=self.source,
                source_status=SourceStatus.UNAVAILABLE,
                game_id=game.game_id,
                game_datetime=game.game_datetime,
                home_team=game.home_team,
                away_team=game.away_team,
                venue=game.venue,
                currency=_event_currency(payload),
                source_event_id=matched_event.source_event_id,
                source_url=matched_event.source_url,
                checked_at=checked_at,
                notes="SeatGeek event found, but no public lowest price is currently available.",
            )

        return PriceObservation(
            source=self.source,
            source_status=SourceStatus.PARTIAL,
            game_id=game.game_id,
            game_datetime=game.game_datetime,
            home_team=game.home_team,
            away_team=game.away_team,
            venue=game.venue,
            currency=_event_currency(payload),
            cheapest_price=float(lowest_price),
            price_is_all_in=None,
            source_event_id=matched_event.source_event_id,
            source_url=_event_url(payload) or matched_event.source_url,
            checked_at=checked_at,
            notes=(
                "Uses SeatGeek stats.lowest_price; "
                "the public API does not expose an all-in pricing flag."
            ),
        )

    def _search_event(self, game: ScheduledGame) -> MatchedEvent | None:
        primary_payload = self._request_json(
            "/events",
            params={
                "client_id": self._settings.client_id,
                "performers[home_team].slug": _performer_slug(game.home_team),
                "performers[away_team].slug": _performer_slug(game.away_team),
                "datetime_utc.gte": _isoformat_utc(game.game_datetime - timedelta(hours=12)),
                "datetime_utc.lte": _isoformat_utc(game.game_datetime + timedelta(hours=12)),
                "per_page": "20",
            },
        )
        events = _events_from_payload(primary_payload)
        if not events:
            fallback_payload = self._request_json(
                "/events",
                params={
                    "client_id": self._settings.client_id,
                    "performers[home_team].slug": _performer_slug(game.home_team),
                    "datetime_utc.gte": _isoformat_utc(game.game_datetime - timedelta(hours=12)),
                    "datetime_utc.lte": _isoformat_utc(game.game_datetime + timedelta(hours=12)),
                    "per_page": "20",
                },
            )
            events = _events_from_payload(fallback_payload)

        best_score = -1
        best_event: dict[str, Any] | None = None
        for candidate in events:
            score = _score_candidate(game, candidate)
            if score > best_score:
                best_score = score
                best_event = candidate

        if best_event is None or best_score < 6:
            return None

        source_event_id = best_event.get("id")
        if not isinstance(source_event_id, int):
            return None

        return MatchedEvent(
            source=self.source,
            game_id=game.game_id,
            source_event_id=str(source_event_id),
            source_url=_event_url(best_event),
            matched_at=datetime.now(tz=UTC),
            metadata={"title": str(best_event.get("title", ""))},
        )

    def _get_event_details(self, event_id: str) -> dict[str, Any]:
        return self._request_json(
            f"/events/{event_id}",
            params={"client_id": self._settings.client_id},
        )

    def _request_json(self, path: str, *, params: dict[str, str | None]) -> dict[str, Any]:
        if not self._settings.client_id:
            msg = "SeatGeek client ID is required"
            raise RuntimeError(msg)

        filtered_params = {key: value for key, value in params.items() if value is not None}
        with httpx.Client(
            base_url="https://api.seatgeek.com/2",
            timeout=self._timeout_seconds,
        ) as client:
            response = client.get(path, params=filtered_params)
            response.raise_for_status()
            payload = response.json()
        sleep(self._settings.rate_limit_delay_seconds)
        if not isinstance(payload, dict):
            msg = "SeatGeek returned a non-object payload"
            raise ValueError(msg)
        return payload


def _match_key(source: str, game_id: str) -> str:
    return f"{source}:{game_id}"


def _events_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("events")
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, dict)]


def _performer_slug(team_name: str) -> str:
    return team_name.strip().lower().replace(".", "").replace(" ", "-")


def _isoformat_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _score_candidate(game: ScheduledGame, candidate: dict[str, Any]) -> int:
    score = 0
    title = " ".join(
        str(candidate.get(key, "")).lower() for key in ("title", "short_title")
    ).strip()
    performers = candidate.get("performers")
    if isinstance(performers, list):
        for performer in performers:
            if not isinstance(performer, dict):
                continue
            performer_name = str(performer.get("name", "")).lower()
            performer_slug = str(performer.get("slug", "")).lower()
            if performer.get("home_team") and (
                performer_name == game.home_team.lower()
                or performer_slug == _performer_slug(game.home_team)
            ):
                score += 4
            if performer.get("away_team") and (
                performer_name == game.away_team.lower()
                or performer_slug == _performer_slug(game.away_team)
            ):
                score += 4

    if game.home_team.lower() in title:
        score += 1
    if game.away_team.lower() in title:
        score += 1

    event_date = _event_date(candidate)
    if event_date == game.official_date:
        score += 2

    venue_name = _event_venue_name(candidate).lower()
    if venue_name and venue_name == game.venue.lower():
        score += 3
    elif venue_name and game.venue.lower() in venue_name:
        score += 1
    return score


def _event_date(candidate: dict[str, Any]) -> str | None:
    for key in ("datetime_local", "datetime_utc"):
        value = candidate.get(key)
        if isinstance(value, str) and len(value) >= 10:
            return value[:10]
    return None


def _event_venue_name(candidate: dict[str, Any]) -> str:
    venue = candidate.get("venue")
    if not isinstance(venue, dict):
        return ""
    name = venue.get("name")
    return str(name) if isinstance(name, str) else ""


def _event_currency(candidate: dict[str, Any]) -> str | None:
    venue = candidate.get("venue")
    if not isinstance(venue, dict):
        return None
    country = venue.get("country")
    if country == "US":
        return "USD"
    if country == "CA":
        return "CAD"
    return None


def _event_url(candidate: dict[str, Any]) -> str | None:
    url = candidate.get("url")
    if not isinstance(url, str) or not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://seatgeek.com{url}"
