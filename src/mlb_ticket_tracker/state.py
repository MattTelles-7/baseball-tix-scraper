"""JSON-backed persistence for runtime state and publish deduplication."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import ValidationError

from mlb_ticket_tracker.models import MatchedEvent, ProviderHealth, RuntimeStatus, TrackerState


class StateStore:
    """Manage tracker state persisted as JSON."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> TrackerState:
        """Load tracker state from disk if present."""
        if not self._path.exists():
            return TrackerState()

        try:
            raw_payload = self._path.read_text(encoding="utf-8")
            return TrackerState.model_validate_json(raw_payload)
        except (OSError, ValidationError, json.JSONDecodeError):
            return TrackerState()

    def save(self, state: TrackerState) -> None:
        """Persist tracker state using an atomic file replace."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        serialized = state.model_dump_json(indent=2)

        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._path.parent,
            prefix=".state.",
            suffix=".json",
            delete=False,
        ) as tmp_file:
            tmp_file.write(serialized)
            tmp_path = Path(tmp_file.name)

        tmp_path.replace(self._path)
        try:
            self._path.chmod(0o600)
        except OSError:
            pass

    def remember_match(self, state: TrackerState, *, key: str, match: MatchedEvent) -> TrackerState:
        """Store a provider event match."""
        state.provider_matches[key] = match
        return state

    def forget_match(self, state: TrackerState, *, key: str) -> None:
        """Remove a provider event match from state."""
        state.provider_matches.pop(key, None)

    def remember_provider_health(
        self,
        state: TrackerState,
        *,
        source: str,
        health: ProviderHealth,
    ) -> TrackerState:
        """Store provider health metadata."""
        state.provider_health[source] = health
        return state

    def update_runtime(self, state: TrackerState, runtime: RuntimeStatus) -> TrackerState:
        """Store the latest runtime markers."""
        state.runtime = runtime
        return state

    def track_published_topic(self, state: TrackerState, *, topic: str, payload: str) -> bool:
        """Record a published payload and report whether it changed."""
        previous = state.published_topics.get(topic)
        state.published_topics[topic] = payload
        return previous != payload

    def clear_published_topic(self, state: TrackerState, *, topic: str) -> None:
        """Forget a retained topic after it has been deleted upstream."""
        state.published_topics.pop(topic, None)

    def register_entity(self, state: TrackerState, *, unique_id: str, discovery_topic: str) -> None:
        """Track a dynamic entity that may later need cleanup."""
        state.dynamic_entities[unique_id] = discovery_topic

    def unregister_entity(self, state: TrackerState, *, unique_id: str) -> None:
        """Forget a dynamic entity after it has been deleted."""
        state.dynamic_entities.pop(unique_id, None)
