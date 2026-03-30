"""Service bootstrap helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import SystemRandom
from zoneinfo import ZoneInfo

import structlog

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.models import (
    MatchedEvent,
    ProviderHealth,
    RuntimeStatus,
    ScheduledGame,
    TeamInfo,
    TrackerState,
)
from mlb_ticket_tracker.ports import PublisherPort, ScheduleClientPort
from mlb_ticket_tracker.providers.base import Provider
from mlb_ticket_tracker.providers.seatgeek import SeatGeekProvider
from mlb_ticket_tracker.providers.ticketmaster import TicketmasterProvider
from mlb_ticket_tracker.providers.vivid import VividProvider
from mlb_ticket_tracker.publisher import MqttPublisher, build_price_entity_descriptor
from mlb_ticket_tracker.schedule import MlbScheduleClient
from mlb_ticket_tracker.state import StateStore
from mlb_ticket_tracker.teams import resolve_team
from mlb_ticket_tracker.utils import redact_sensitive_text

logger = structlog.get_logger(__name__)
_RANDOM = SystemRandom()


@dataclass(frozen=True)
class ServiceContext:
    """Resolved application dependencies used by the service."""

    settings: Settings
    team: TeamInfo
    state_store: StateStore
    schedule_client: ScheduleClientPort


def build_service_context(settings: Settings) -> ServiceContext:
    """Construct the baseline dependencies used by the app."""
    return ServiceContext(
        settings=settings,
        team=resolve_team(settings.team_id, settings.team_slug, settings.team_name),
        state_store=StateStore(settings.state_path),
        schedule_client=MlbScheduleClient(timeout_seconds=settings.http_timeout_seconds),
    )


def initialize_runtime_state(
    *,
    state_store: StateStore,
    state: TrackerState,
    poll_interval_minutes: int,
    timezone: str,
) -> TrackerState:
    """Initialize heartbeat and poll timing metadata at startup."""
    now = datetime.now(tz=ZoneInfo(timezone))
    runtime = RuntimeStatus(
        last_started_poll_at=state.runtime.last_started_poll_at,
        last_completed_poll_at=state.runtime.last_completed_poll_at,
        last_heartbeat_at=now,
        next_poll_at=now + timedelta(minutes=poll_interval_minutes),
        last_error_at=state.runtime.last_error_at,
        last_error=state.runtime.last_error,
    )
    updated_state = state_store.update_runtime(state, runtime)
    state_store.save(updated_state)
    next_poll_at = runtime.next_poll_at.isoformat() if runtime.next_poll_at else None
    logger.info("runtime_initialized", next_poll_at=next_poll_at)
    return updated_state


class TrackerService:
    """Long-running service that polls ticket providers and publishes MQTT updates."""

    def __init__(
        self,
        context: ServiceContext,
        *,
        publisher: PublisherPort | None = None,
        providers: list[Provider] | None = None,
    ) -> None:
        self._context = context
        self._publisher = publisher or MqttPublisher(context.settings)
        self._providers = providers or _build_providers(context.settings)

    def run_forever(self) -> None:
        """Run the polling loop until interrupted."""
        state = self._context.state_store.load()
        state = initialize_runtime_state(
            state_store=self._context.state_store,
            state=state,
            poll_interval_minutes=self._context.settings.poll_interval_minutes,
            timezone=self._context.settings.timezone,
        )
        logger.info(
            "service_started",
            team=self._context.team.slug,
            providers=[provider.source for provider in self._providers],
            poll_interval_minutes=self._context.settings.poll_interval_minutes,
            failure_retry_seconds=self._context.settings.failure_retry_seconds,
            dry_run=self._context.settings.dry_run,
            data_dir=str(self._context.settings.data_dir),
        )
        try:
            while True:
                cycle_started = datetime.now(tz=ZoneInfo(self._context.settings.timezone))
                try:
                    self._publisher.connect()
                    state = self._run_cycle(state=state, cycle_started=cycle_started)
                    sleep_seconds = (
                        self._context.settings.poll_interval_minutes * 60
                    ) + _RANDOM.uniform(
                        0,
                        self._context.settings.request_jitter_seconds,
                    )
                    logger.info("service_sleep_scheduled", sleep_seconds=round(sleep_seconds, 3))
                except Exception as exc:
                    runtime = _runtime_failure(
                        previous=state.runtime,
                        occurred_at=cycle_started,
                        retry_seconds=self._context.settings.failure_retry_seconds,
                        error=redact_sensitive_text(str(exc)),
                    )
                    state = self._context.state_store.update_runtime(state, runtime)
                    self._context.state_store.save(state)
                    sleep_seconds = self._context.settings.failure_retry_seconds
                    logger.error(
                        "service_iteration_failed",
                        retry_in_seconds=sleep_seconds,
                        error=redact_sensitive_text(str(exc)),
                        error_type=type(exc).__name__,
                    )
                time.sleep(sleep_seconds)
        finally:
            self._publisher.close()

    def _run_cycle(self, *, state: TrackerState, cycle_started: datetime) -> TrackerState:
        runtime = self._start_cycle(state=state, cycle_started=cycle_started)
        games = self._fetch_games()
        active_unique_ids: set[str] = set()

        for provider in self._providers:
            active_unique_ids.update(
                self._run_provider_cycle(
                    provider=provider,
                    games=games,
                    state=state,
                    cycle_started=cycle_started,
                )
            )

        self._publisher.cleanup_stale_dynamic_entities(
            active_unique_ids=active_unique_ids,
            state_store=self._context.state_store,
            state=state,
        )

        completed_at = datetime.now(tz=ZoneInfo(self._context.settings.timezone))
        runtime = self._complete_cycle_runtime(runtime=runtime, completed_at=completed_at)
        state = self._context.state_store.update_runtime(state, runtime)
        self._publish_service_metrics(
            team=self._context.team,
            tracked_games=len(games),
            runtime=runtime,
            completed_at=completed_at,
            state=state,
        )
        self._context.state_store.save(state)
        logger.info(
            "poll_cycle_completed",
            tracked_games=len(games),
            providers=len(self._providers),
            next_poll_at=(runtime.next_poll_at.isoformat() if runtime.next_poll_at else None),
        )
        return state

    def _start_cycle(self, *, state: TrackerState, cycle_started: datetime) -> RuntimeStatus:
        runtime = RuntimeStatus(
            last_started_poll_at=cycle_started,
            last_completed_poll_at=state.runtime.last_completed_poll_at,
            last_heartbeat_at=cycle_started,
            next_poll_at=cycle_started
            + timedelta(minutes=self._context.settings.poll_interval_minutes),
            last_error_at=state.runtime.last_error_at,
            last_error=state.runtime.last_error,
        )
        self._context.state_store.update_runtime(state, runtime)
        self._context.state_store.save(state)
        logger.info(
            "poll_cycle_started",
            team=self._context.team.slug,
            providers=[provider.source for provider in self._providers],
        )
        return runtime

    def _fetch_games(self) -> list[ScheduledGame]:
        return self._context.schedule_client.fetch_upcoming_games(
            team=self._context.team,
            lookahead_days=self._context.settings.lookahead_days,
            home_games_only=self._context.settings.home_games_only,
            timezone=self._context.settings.timezone,
            grace_minutes=self._context.settings.post_game_grace_minutes,
        )

    def _run_provider_cycle(
        self,
        *,
        provider: Provider,
        games: list[ScheduledGame],
        state: TrackerState,
        cycle_started: datetime,
    ) -> set[str]:
        capability = provider.capability_report()
        configured = provider.healthcheck()
        health = state.provider_health.get(provider.source, ProviderHealth())

        if _in_backoff(health=health, now=cycle_started):
            logger.warning(
                "provider_in_backoff",
                source=provider.source,
                backoff_until=health.backoff_until.isoformat() if health.backoff_until else None,
            )
            active_unique_ids = self._expected_dynamic_entity_ids(
                games=games,
                source=provider.source,
            )
            self._publisher.publish_provider_health(
                team=self._context.team,
                capability=capability,
                health=health,
                state_store=self._context.state_store,
                state=state,
                healthy=False,
                configured=True,
            )
            return active_unique_ids

        if not configured:
            logger.warning("provider_unconfigured", source=provider.source)
            self._publisher.publish_provider_health(
                team=self._context.team,
                capability=capability,
                health=health,
                state_store=self._context.state_store,
                state=state,
                healthy=False,
                configured=False,
            )
            return set()

        active_unique_ids = self._expected_dynamic_entity_ids(games=games, source=provider.source)
        try:
            current_matches = self._refresh_cached_matches(
                provider=provider,
                state=state,
                now=cycle_started,
            )
            new_matches = provider.match_events(games, current_matches)
            current_matches = self._remember_provider_matches(
                state=state,
                provider=provider,
                existing_matches=current_matches,
                new_matches=new_matches,
            )
            self._publish_provider_observations(
                provider=provider,
                games=games,
                state=state,
                matches=current_matches,
            )

            health = ProviderHealth(
                consecutive_failures=0,
                last_successful_poll_at=cycle_started.astimezone(UTC),
                last_error_at=None,
                last_error=None,
                backoff_until=None,
            )
            self._context.state_store.remember_provider_health(
                state,
                source=provider.source,
                health=health,
            )
            self._publisher.publish_provider_health(
                team=self._context.team,
                capability=capability,
                health=health,
                state_store=self._context.state_store,
                state=state,
                healthy=True,
                configured=True,
            )
            return active_unique_ids
        except Exception as exc:
            safe_error = redact_sensitive_text(str(exc))
            health = _failure_health(previous=health, now=cycle_started, error=safe_error)
            self._context.state_store.remember_provider_health(
                state,
                source=provider.source,
                health=health,
            )
            self._publisher.publish_provider_health(
                team=self._context.team,
                capability=capability,
                health=health,
                state_store=self._context.state_store,
                state=state,
                healthy=False,
                configured=True,
            )
            logger.error(
                "provider_cycle_failed",
                source=provider.source,
                error=safe_error,
                error_type=type(exc).__name__,
            )
            return active_unique_ids

    def _refresh_cached_matches(
        self,
        *,
        provider: Provider,
        state: TrackerState,
        now: datetime,
    ) -> dict[str, MatchedEvent]:
        fresh_matches: dict[str, MatchedEvent] = {}
        ttl_cutoff = now.astimezone(UTC) - timedelta(
            hours=self._context.settings.match_cache_ttl_hours
        )
        for key, match in list(state.provider_matches.items()):
            if not key.startswith(f"{provider.source}:"):
                continue
            if match.matched_at < ttl_cutoff:
                self._context.state_store.forget_match(state, key=key)
                logger.info(
                    "provider_match_expired",
                    source=provider.source,
                    game_id=match.game_id,
                    source_event_id=match.source_event_id,
                    matched_at=match.matched_at.isoformat(),
                    ttl_hours=self._context.settings.match_cache_ttl_hours,
                )
                continue
            fresh_matches[key] = match
        return fresh_matches

    def _remember_provider_matches(
        self,
        *,
        state: TrackerState,
        provider: Provider,
        existing_matches: dict[str, MatchedEvent],
        new_matches: dict[str, MatchedEvent],
    ) -> dict[str, MatchedEvent]:
        merged_matches = dict(existing_matches)
        for key, matched_event in new_matches.items():
            self._context.state_store.remember_match(
                state,
                key=key,
                match=matched_event,
            )
            merged_matches[key] = matched_event
        logger.info(
            "provider_matches_refreshed",
            source=provider.source,
            cached_matches=len(existing_matches),
            new_matches=len(new_matches),
        )
        return merged_matches

    def _publish_provider_observations(
        self,
        *,
        provider: Provider,
        games: list[ScheduledGame],
        state: TrackerState,
        matches: dict[str, MatchedEvent],
    ) -> None:
        for game in games:
            match_key = f"{provider.source}:{game.game_id}"
            observation = provider.fetch_lowest_price(game, matches.get(match_key))
            self._publisher.publish_price_observation(
                team=self._context.team,
                game=game,
                observation=observation,
                state_store=self._context.state_store,
                state=state,
            )

    def _publish_service_metrics(
        self,
        *,
        team: TeamInfo,
        tracked_games: int,
        runtime: RuntimeStatus,
        completed_at: datetime,
        state: TrackerState,
    ) -> None:
        self._publisher.publish_service_metrics(
            team=team,
            tracked_games=tracked_games,
            next_poll_at=runtime.next_poll_at or completed_at,
            last_completed_poll_at=runtime.last_completed_poll_at,
            state_store=self._context.state_store,
            state=state,
        )

    def _complete_cycle_runtime(
        self,
        *,
        runtime: RuntimeStatus,
        completed_at: datetime,
    ) -> RuntimeStatus:
        return RuntimeStatus(
            last_started_poll_at=runtime.last_started_poll_at,
            last_completed_poll_at=completed_at,
            last_heartbeat_at=completed_at,
            next_poll_at=runtime.next_poll_at,
            last_error_at=None,
            last_error=None,
        )

    def _expected_dynamic_entity_ids(
        self,
        *,
        games: list[ScheduledGame],
        source: str,
    ) -> set[str]:
        return _expected_dynamic_entity_ids(
            team=self._context.team,
            games=games,
            source=source,
            settings=self._context.settings,
        )


def _build_providers(settings: Settings) -> list[Provider]:
    providers: list[Provider] = []
    if settings.enable_ticketmaster:
        providers.append(
            TicketmasterProvider(
                settings=settings.ticketmaster,
                timeout_seconds=settings.http_timeout_seconds,
            )
        )
    if settings.enable_seatgeek:
        providers.append(SeatGeekProvider(settings.seatgeek))
    if settings.enable_vivid and settings.enable_experimental_adapters:
        providers.append(VividProvider(settings.vivid))
    return providers


def _in_backoff(*, health: ProviderHealth, now: datetime) -> bool:
    return health.backoff_until is not None and health.backoff_until > now.astimezone(UTC)


def _failure_health(*, previous: ProviderHealth, now: datetime, error: str) -> ProviderHealth:
    failures = previous.consecutive_failures + 1
    backoff_minutes = min(2**failures, 60)
    return ProviderHealth(
        consecutive_failures=failures,
        last_successful_poll_at=previous.last_successful_poll_at,
        last_error_at=now.astimezone(UTC),
        last_error=error,
        backoff_until=now.astimezone(UTC) + timedelta(minutes=backoff_minutes),
    )


def _expected_dynamic_entity_ids(
    *,
    team: TeamInfo,
    games: list[ScheduledGame],
    source: str,
    settings: Settings,
) -> set[str]:
    return {
        build_price_entity_descriptor(
            settings=settings,
            team=team,
            game=game,
            source=source,
            currency=None,
        ).unique_id
        for game in games
    }


def _runtime_failure(
    *,
    previous: RuntimeStatus,
    occurred_at: datetime,
    retry_seconds: float,
    error: str,
) -> RuntimeStatus:
    return RuntimeStatus(
        last_started_poll_at=occurred_at,
        last_completed_poll_at=previous.last_completed_poll_at,
        last_heartbeat_at=occurred_at,
        next_poll_at=occurred_at + timedelta(seconds=retry_seconds),
        last_error_at=occurred_at.astimezone(UTC),
        last_error=error,
    )
