from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from mlb_ticket_tracker.config import Settings
from mlb_ticket_tracker.validation import validate_settings


def test_validate_settings_accepts_ticketmaster_only_config(
    settings_factory: Callable[..., Settings],
) -> None:
    settings = settings_factory(
        TICKETMASTER_API_KEY="ticketmaster-key",
    )

    report = validate_settings(settings)

    assert report.ok is True
    assert report.errors == []
    assert report.warnings == []
    assert report.details["dry_run"] is False
    assert report.details["data_dir_status"] == "writable"


def test_validate_settings_rejects_missing_ticketmaster_key(
    settings_factory: Callable[..., Settings],
) -> None:
    settings = settings_factory(
        ENABLE_TICKETMASTER=True,
        TICKETMASTER_API_KEY=None,
    )

    report = validate_settings(settings)

    assert report.ok is False
    assert "ENABLE_TICKETMASTER=true requires TICKETMASTER_API_KEY." in report.errors


def test_validate_settings_warns_for_scaffold_providers(
    settings_factory: Callable[..., Settings],
) -> None:
    settings = settings_factory(
        TICKETMASTER_API_KEY="ticketmaster-key",
        ENABLE_SEATGEEK=True,
        ENABLE_VIVID=True,
        ENABLE_EXPERIMENTAL_ADAPTERS=False,
    )

    report = validate_settings(settings)

    assert report.ok is True
    assert (
        "SeatGeek is scaffold only in this release. Keep ENABLE_SEATGEEK=false."
        in report.warnings
    )
    assert (
        "Vivid is scaffold only in this release. Keep ENABLE_VIVID=false for first deployment."
        in report.warnings
    )
    assert (
        "ENABLE_VIVID=true has no effect unless ENABLE_EXPERIMENTAL_ADAPTERS=true."
        in report.warnings
    )


def test_validate_settings_rejects_non_directory_data_dir(
    settings_factory: Callable[..., Settings],
    tmp_path: Path,
) -> None:
    not_a_directory = tmp_path / "state.json"
    not_a_directory.write_text("{}", encoding="utf-8")
    settings = settings_factory(
        TICKETMASTER_API_KEY="ticketmaster-key",
        DATA_DIR=str(not_a_directory),
    )

    report = validate_settings(settings)

    assert report.ok is False
    assert report.details["data_dir_status"] == "not_a_directory"
    assert f"DATA_DIR is not a directory: {not_a_directory}" in report.errors


def test_settings_reject_invalid_timezone(settings_factory: Callable[..., Settings]) -> None:
    with pytest.raises(ValidationError, match="unknown timezone"):
        settings_factory(
            TIMEZONE="Mars/Olympus_Mons",
        )
