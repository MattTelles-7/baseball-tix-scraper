"""Shared utility helpers."""

from __future__ import annotations

import re

_QUERY_SECRET_PATTERN = re.compile(
    r"(?i)(apikey|api_key|token|access_token|refresh_token|password|secret|client_secret)=([^&\s]+)"
)
_KEY_VALUE_SECRET_PATTERN = re.compile(
    r'(?i)("?(apikey|api_key|token|access_token|refresh_token|password|secret|client_secret)"?\s*[:=]\s*"?)([^",\s}]+)'
)
_BEARER_PATTERN = re.compile(r"(?i)(authorization[:=]\s*bearer\s+)([^\s,]+)")


def slugify(value: str) -> str:
    """Convert free-form text into a deterministic MQTT-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return slug.strip("_")


def redact_sensitive_text(value: str) -> str:
    """Redact common credential patterns from logs, state, and health output."""
    redacted = _QUERY_SECRET_PATTERN.sub(r"\1=[redacted]", value)
    redacted = _KEY_VALUE_SECRET_PATTERN.sub(r"\1[redacted]", redacted)
    redacted = _BEARER_PATTERN.sub(r"\1[redacted]", redacted)
    return redacted
