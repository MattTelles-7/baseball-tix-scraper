"""Configuration loading for the ticket tracker service."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderSettings(BaseModel):
    """Shared configuration shape for provider adapters."""

    model_config = ConfigDict(frozen=True)

    enabled: bool
    rate_limit_delay_seconds: float


class TicketmasterSettings(ProviderSettings):
    """Configuration for the Ticketmaster provider."""

    api_key: str | None = None


class SeatGeekSettings(ProviderSettings):
    """Configuration for the SeatGeek provider."""

    client_id: str | None = None
    client_secret: str | None = None


class VividSettings(ProviderSettings):
    """Configuration for the Vivid provider."""

    api_token: str | None = None


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    team_id: int | None = Field(default=None, alias="TEAM_ID")
    team_slug: str | None = Field(default=None, alias="TEAM_SLUG")
    team_name: str | None = Field(default=None, alias="TEAM_NAME")
    home_games_only: bool = Field(default=True, alias="HOME_GAMES_ONLY")
    lookahead_days: int = Field(default=60, alias="LOOKAHEAD_DAYS")
    poll_interval_minutes: int = Field(default=15, alias="POLL_INTERVAL_MINUTES")
    timezone: str = Field(default="America/New_York", alias="TIMEZONE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    post_game_grace_minutes: int = Field(default=240, alias="POST_GAME_GRACE_MINUTES")
    dry_run: bool = Field(default=False, alias="DRY_RUN")
    verbose_debug: bool = Field(default=False, alias="VERBOSE_DEBUG")
    http_timeout_seconds: float = Field(default=20.0, alias="HTTP_TIMEOUT_SECONDS")
    request_jitter_seconds: float = Field(default=5.0, alias="REQUEST_JITTER_SECONDS")
    mqtt_host: str = Field(alias="MQTT_HOST")
    mqtt_port: int = Field(default=1883, alias="MQTT_PORT")
    mqtt_username: str | None = Field(default=None, alias="MQTT_USERNAME")
    mqtt_password: str | None = Field(default=None, alias="MQTT_PASSWORD")
    mqtt_topic_prefix: str = Field(default="mlb_ticket_tracker", alias="MQTT_TOPIC_PREFIX")
    mqtt_discovery_prefix: str = Field(default="homeassistant", alias="MQTT_DISCOVERY_PREFIX")
    mqtt_client_id: str = Field(default="mlb-ticket-tracker", alias="MQTT_CLIENT_ID")
    mqtt_keepalive: int = Field(default=60, alias="MQTT_KEEPALIVE")
    enable_ticketmaster: bool = Field(default=True, alias="ENABLE_TICKETMASTER")
    enable_seatgeek: bool = Field(default=False, alias="ENABLE_SEATGEEK")
    enable_vivid: bool = Field(default=False, alias="ENABLE_VIVID")
    enable_experimental_adapters: bool = Field(
        default=False,
        alias="ENABLE_EXPERIMENTAL_ADAPTERS",
    )
    ticketmaster_api_key: str | None = Field(default=None, alias="TICKETMASTER_API_KEY")
    seatgeek_client_id: str | None = Field(default=None, alias="SEATGEEK_CLIENT_ID")
    seatgeek_client_secret: str | None = Field(default=None, alias="SEATGEEK_CLIENT_SECRET")
    vivid_api_token: str | None = Field(default=None, alias="VIVID_API_TOKEN")
    ticketmaster_rate_limit_delay_seconds: float = Field(
        default=0.5,
        alias="TICKETMASTER_RATE_LIMIT_DELAY_SECONDS",
    )
    seatgeek_rate_limit_delay_seconds: float = Field(
        default=0.5,
        alias="SEATGEEK_RATE_LIMIT_DELAY_SECONDS",
    )
    vivid_rate_limit_delay_seconds: float = Field(
        default=1.0,
        alias="VIVID_RATE_LIMIT_DELAY_SECONDS",
    )

    @field_validator("lookahead_days", "poll_interval_minutes", "post_game_grace_minutes")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        """Ensure integer configuration values are positive."""
        if value <= 0:
            msg = "value must be positive"
            raise ValueError(msg)
        return value

    @field_validator(
        "http_timeout_seconds",
        "request_jitter_seconds",
        "ticketmaster_rate_limit_delay_seconds",
        "seatgeek_rate_limit_delay_seconds",
        "vivid_rate_limit_delay_seconds",
    )
    @classmethod
    def validate_non_negative_float(cls, value: float) -> float:
        """Ensure numeric delay values are not negative."""
        if value < 0:
            msg = "value must be non-negative"
            raise ValueError(msg)
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize log-level input for logging configuration."""
        return value.upper()

    @property
    def state_path(self) -> Path:
        """Location of the persistent JSON state file."""
        return self.data_dir / "state.json"

    @property
    def ticketmaster(self) -> TicketmasterSettings:
        """Provider-specific Ticketmaster settings."""
        return TicketmasterSettings(
            enabled=self.enable_ticketmaster,
            rate_limit_delay_seconds=self.ticketmaster_rate_limit_delay_seconds,
            api_key=self.ticketmaster_api_key,
        )

    @property
    def seatgeek(self) -> SeatGeekSettings:
        """Provider-specific SeatGeek settings."""
        return SeatGeekSettings(
            enabled=self.enable_seatgeek,
            rate_limit_delay_seconds=self.seatgeek_rate_limit_delay_seconds,
            client_id=self.seatgeek_client_id,
            client_secret=self.seatgeek_client_secret,
        )

    @property
    def vivid(self) -> VividSettings:
        """Provider-specific Vivid settings."""
        return VividSettings(
            enabled=self.enable_vivid,
            rate_limit_delay_seconds=self.vivid_rate_limit_delay_seconds,
            api_token=self.vivid_api_token,
        )


def load_settings() -> Settings:
    """Load application settings from the environment."""
    return Settings()  # type: ignore[call-arg]
