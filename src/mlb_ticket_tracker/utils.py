"""Shared utility helpers."""

from __future__ import annotations

import re


def slugify(value: str) -> str:
    """Convert free-form text into a deterministic MQTT-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return slug.strip("_")
