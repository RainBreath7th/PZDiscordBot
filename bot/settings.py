from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    """Invalid environment or YAML. Fatal on startup."""


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required")
    return value


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    discord_token: str
    rcon_host: str
    rcon_port: int
    rcon_password: str
    poll_interval: int
    restart_timeout: int
    restart_grace: int
    rcon_fail_threshold: int
    empty_confirm_seconds: int
    rcon_timeout: float
    config_dir: Path
    health_state_path: Path
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        port = _env_int("RCON_PORT", 0)
        if port <= 0:
            raise ConfigError("RCON_PORT is required and must be > 0")
        config_dir = Path(os.environ.get("CONFIG_DIR", "config")).expanduser()
        health = Path(
            os.environ.get("HEALTH_STATE_PATH", "/tmp/pz-bot-health.json")
        ).expanduser()
        return cls(
            discord_token=_require_env("DISCORD_TOKEN"),
            rcon_host=_require_env("RCON_HOST"),
            rcon_port=port,
            rcon_password=_require_env("RCON_PASSWORD"),
            poll_interval=_env_int("POLL_INTERVAL", 30),
            restart_timeout=_env_int("RESTART_TIMEOUT", 7200),
            restart_grace=_env_int("RESTART_GRACE", 360),
            rcon_fail_threshold=_env_int("RCON_FAIL_THRESHOLD", 3),
            empty_confirm_seconds=_env_int("EMPTY_CONFIRM_SECONDS", 10),
            rcon_timeout=float(os.environ.get("RCON_TIMEOUT", "10")),
            config_dir=config_dir,
            health_state_path=health,
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
