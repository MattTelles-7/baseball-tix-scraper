"""Ticketmaster provider using the official Discovery API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Any

import httpx

from mlb_ticket_tracker.config import TicketmasterSettings
from mlb_ticket_tracker.models import (
    MatchedEvent,
    PriceObservation,
    ProviderCapability,
    ScheduledGame,
    SourceStatus,
)
from mlb_ticket_tracker.providers.base import Provider


class TicketmasterProvider(Provider):
    """Ticketmaster Discovery API adapter."""

    source = "ticketmaster"

    def __init__(
        self,
        *,
        settings: TicketmasterSettings,
        timeout_seconds: float,
    ) -> None:
        self._settings = settings
        self._timeout_seconds = timeout_seconds

    def capability_report(self) -> ProviderCapability:
        return ProviderCapability(
            source=self.source,
            source_status=SourceStatus.SUPPORTED,
            auth_required=True,
            implemented_fields=("priceRanges.min", "event_url", "event_id"),
            limitations=(
                "Uses Discovery API priceRanges.min rather than privileged live inventory data.",
                "May not match the true lowest live listing price in all cases.",
            ),
        )

    def healthcheck(self) -> bool:
        return bool(self._settings.api_key)

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
                notes="No Ticketmaster event match found for this game.",
            )

        payload = self._get_event_details(matched_event.source_event_id)
        price_ranges = payload.get("priceRanges")
        if not isinstance(price_ranges, list) or not price_ranges:
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
                notes="Ticketmaster event found, but no public price range is currently available.",
            )

        minimums = [
            item["min"]
            for item in price_ranges
            if isinstance(item, dict) and isinstance(item.get("min"), (int, float))
        ]
        currency = next(
            (
                item["currency"]
                for item in price_ranges
                if isinstance(item, dict) and isinstance(item.get("currency"), str)
            ),
            None,
        )
        if not minimums:
            return PriceObservation(
                source=self.source,
                source_status=SourceStatus.UNAVAILABLE,
                game_id=game.game_id,
                game_datetime=game.game_datetime,
                home_team=game.home_team,
                away_team=game.away_team,
                venue=game.venue,
                currency=currency,
                source_event_id=matched_event.source_event_id,
                source_url=matched_event.source_url,
                checked_at=checked_at,
                notes="Ticketmaster returned price ranges without a minimum value.",
            )

        return PriceObservation(
            source=self.source,
            source_status=SourceStatus.SUPPORTED,
            game_id=game.game_id,
            game_datetime=game.game_datetime,
            home_team=game.home_team,
            away_team=game.away_team,
            venue=game.venue,
            currency=currency,
            cheapest_price=float(min(minimums)),
            price_is_all_in=False,
            source_event_id=matched_event.source_event_id,
            source_url=_event_url(payload) or matched_event.source_url,
            checked_at=checked_at,
            notes=(
                "Uses Ticketmaster Discovery API priceRanges.min; "
                "it may differ from the live lowest listing."
            ),
        )

    def _search_event(self, game: ScheduledGame) -> MatchedEvent | None:
        payload = self._request_json(
            "/events.json",
            params={
                "apikey": self._settings.api_key,
                "keyword": f"{game.away_team} {game.home_team}",
                "countryCode": "US",
                "segmentName": "Sports",
                "startDateTime": (game.game_datetime - timedelta(hours=12))
                .isoformat()
                .replace(
                    "+00:00",
                    "Z",
                ),
                "endDateTime": (game.game_datetime + timedelta(hours=12))
                .isoformat()
                .replace(
                    "+00:00",
                    "Z",
                ),
                "size": "20",
            },
        )
        embedded = payload.get("_embedded")
        if not isinstance(embedded, dict):
            return None
        events = embedded.get("events")
        if not isinstance(events, list):
            return None

        best_score = -1
        best_event: dict[str, Any] | None = None
        for candidate in events:
            if not isinstance(candidate, dict):
                continue
            score = _score_candidate(game, candidate)
            if score > best_score:
                best_score = score
                best_event = candidate

        if best_event is None or best_score < 5:
            return None

        source_event_id = best_event.get("id")
        if not isinstance(source_event_id, str):
            return None
        return MatchedEvent(
            source=self.source,
            game_id=game.game_id,
            source_event_id=source_event_id,
            source_url=_event_url(best_event),
            matched_at=datetime.now(tz=UTC),
            metadata={"name": str(best_event.get("name", ""))},
        )

    def _get_event_details(self, event_id: str) -> dict[str, Any]:
        return self._request_json(
            f"/events/{event_id}.json",
            params={"apikey": self._settings.api_key},
        )

    def _request_json(self, path: str, *, params: dict[str, str | None]) -> dict[str, Any]:
        if not self._settings.api_key:
            msg = "Ticketmaster API key is required"
            raise RuntimeError(msg)

        filtered_params = {key: value for key, value in params.items() if value is not None}
        with httpx.Client(
            base_url="https://app.ticketmaster.com/discovery/v2",
            timeout=self._timeout_seconds,
        ) as client:
            response = client.get(path, params=filtered_params)
            response.raise_for_status()
            payload = response.json()
        sleep(self._settings.rate_limit_delay_seconds)
        if not isinstance(payload, dict):
            msg = "Ticketmaster returned a non-object payload"
            raise ValueError(msg)
        return payload


def _match_key(source: str, game_id: str) -> str:
    return f"{source}:{game_id}"


def _score_candidate(game: ScheduledGame, candidate: dict[str, Any]) -> int:
    name = str(candidate.get("name", "")).lower()
    score = 0
    if game.home_team.lower() in name:
        score += 3
    if game.away_team.lower() in name:
        score += 3
    if game.official_date == _event_local_date(candidate):
        score += 2
    venue_name = _event_venue_name(candidate).lower()
    if venue_name and venue_name == game.venue.lower():
        score += 3
    elif venue_name and game.venue.lower() in venue_name:
        score += 1
    return score


def _event_local_date(candidate: dict[str, Any]) -> str | None:
    dates = candidate.get("dates")
    if not isinstance(dates, dict):
        return None
    start = dates.get("start")
    if not isinstance(start, dict):
        return None
    local_date = start.get("localDate")
    return local_date if isinstance(local_date, str) else None


def _event_url(candidate: dict[str, Any]) -> str | None:
    url = candidate.get("url")
    return url if isinstance(url, str) else None


def _event_venue_name(candidate: dict[str, Any]) -> str:
    embedded = candidate.get("_embedded")
    if not isinstance(embedded, dict):
        return ""
    venues = embedded.get("venues")
    if not isinstance(venues, list) or not venues:
        return ""
    venue = venues[0]
    if not isinstance(venue, dict):
        return ""
    name = venue.get("name")
    return name if isinstance(name, str) else ""
