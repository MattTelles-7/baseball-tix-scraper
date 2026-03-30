"""Config validation helpers for first-run checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.teams import resolve_team


@dataclass(frozen=True)
class ValidationReport:
    """Summary of config validation for safe first startup."""

    ok: bool
    summary: str
    errors: list[str]
    warnings: list[str]
    details: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Convert the report into a JSON-serializable dictionary."""
        return asdict(self)


def validate_settings(settings: Settings) -> ValidationReport:
    """Validate settings without contacting external services."""
    errors: list[str] = []
    warnings: list[str] = []

    team = resolve_team(settings.team_id, settings.team_slug, settings.team_name)
    data_dir_status = _validate_data_dir(settings.data_dir, errors)

    enabled_provider_count = (
        int(settings.enable_ticketmaster)
        + int(settings.enable_seatgeek)
        + int(settings.enable_vivid)
    )
    if enabled_provider_count == 0:
        errors.append(
            "No providers are enabled. Set ENABLE_TICKETMASTER=true for a first deployment."
        )

    if settings.enable_ticketmaster and not settings.ticketmaster_api_key:
        errors.append("ENABLE_TICKETMASTER=true requires TICKETMASTER_API_KEY.")

    if settings.enable_seatgeek:
        warnings.append("SeatGeek is scaffold only in this release. Keep ENABLE_SEATGEEK=false.")
        if not settings.seatgeek_client_id:
            warnings.append("ENABLE_SEATGEEK=true is set without SEATGEEK_CLIENT_ID.")

    if settings.enable_vivid:
        warnings.append(
            "Vivid is scaffold only in this release. Keep ENABLE_VIVID=false for first deployment."
        )
        if not settings.enable_experimental_adapters:
            warnings.append(
                "ENABLE_VIVID=true has no effect unless ENABLE_EXPERIMENTAL_ADAPTERS=true."
            )
        if not settings.vivid_api_token:
            warnings.append("ENABLE_VIVID=true is set without VIVID_API_TOKEN.")

    if bool(settings.mqtt_username) != bool(settings.mqtt_password):
        warnings.append("Set both MQTT_USERNAME and MQTT_PASSWORD, or leave both empty.")

    details: dict[str, object] = {
        "team": {
            "id": team.id,
            "slug": team.slug,
            "name": team.name,
            "venue": team.venue,
        },
        "timezone": settings.timezone,
        "home_games_only": settings.home_games_only,
        "lookahead_days": settings.lookahead_days,
        "poll_interval_minutes": settings.poll_interval_minutes,
        "match_cache_ttl_hours": settings.match_cache_ttl_hours,
        "post_game_grace_minutes": settings.post_game_grace_minutes,
        "data_dir": str(settings.data_dir),
        "data_dir_status": data_dir_status,
        "dry_run": settings.dry_run,
        "mqtt": {
            "host": settings.mqtt_host,
            "port": settings.mqtt_port,
            "topic_prefix": settings.mqtt_topic_prefix,
            "discovery_prefix": settings.mqtt_discovery_prefix,
            "username_set": bool(settings.mqtt_username),
            "password_set": bool(settings.mqtt_password),
        },
        "providers": {
            "ticketmaster": {
                "enabled": settings.enable_ticketmaster,
                "configured": bool(settings.ticketmaster_api_key),
            },
            "seatgeek": {
                "enabled": settings.enable_seatgeek,
                "configured": bool(settings.seatgeek_client_id),
            },
            "vivid": {
                "enabled": settings.enable_vivid,
                "experimental_adapters": settings.enable_experimental_adapters,
                "configured": bool(settings.vivid_api_token),
            },
        },
    }

    summary = (
        "configuration is valid for startup" if not errors else "configuration has blocking issues"
    )
    return ValidationReport(
        ok=not errors,
        summary=summary,
        errors=errors,
        warnings=warnings,
        details=details,
    )


def _validate_data_dir(data_dir: Path, errors: list[str]) -> str:
    """Confirm that the configured data directory is writable."""
    if data_dir.exists() and not data_dir.is_dir():
        errors.append(f"DATA_DIR is not a directory: {data_dir}")
        return "not_a_directory"

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=data_dir, prefix=".validate.", delete=True):
            pass
    except OSError as exc:
        errors.append(f"DATA_DIR is not writable: {data_dir} ({exc})")
        return "not_writable"
    return "writable"
