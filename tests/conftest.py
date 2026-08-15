from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bot.config import ConfigStore
from bot.settings import Settings


def write_bundle(root: Path, *, guilds: dict | None = None) -> Path:
    (root / "locales").mkdir(parents=True, exist_ok=True)
    guilds = guilds or {
        "111": {
            "admin_role_ids": ["10"],
            "member_role_ids": ["20"],
            "command_channel_ids": [],
            "break_glass_user_ids": ["99"],
            "command_min_tier": {},
        }
    }
    (root / "permissions.yaml").write_text(
        yaml.safe_dump({"guilds": guilds}),
        encoding="utf-8",
    )
    (root / "i18n.yaml").write_text(
        yaml.safe_dump(
            {"discord_locales": ["zh", "en", "jp"], "game_locales": ["zh", "en"]}
        ),
        encoding="utf-8",
    )
    (root / "limits.yaml").write_text(
        yaml.safe_dump(
            {
                "item_count": {"min": 1, "max": 50},
                "xp": {"min": 1, "max": 100000},
                "vehicle": 1,
                "horde": {"min": 1, "max": 50},
                "servermsg_max_chars": 20,
                "confirm_timeout_seconds": 30,
            }
        ),
        encoding="utf-8",
    )
    for locale, queued in (
        ("zh", "排队重启。" + "长" * 40),
        ("en", "Restart queued. " + "long " * 20),
        ("jp", "キューしました。" + "長" * 40),
    ):
        (root / "locales" / f"{locale}.yaml").write_text(
            yaml.safe_dump(
                {
                    "restart": {"queued": queued, "timeout": "timeout {seconds}"},
                    "error": {"rcon_failed": "fail {detail}"},
                }
            ),
            encoding="utf-8",
        )
    return root


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return write_bundle(tmp_path)


@pytest.fixture
def store(config_dir: Path) -> ConfigStore:
    return ConfigStore(config_dir)


def make_settings(**overrides: object) -> Settings:
    values = dict(
        discord_token="token",
        rcon_host="pz",
        rcon_port=27015,
        rcon_password="secret",
        poll_interval=1,
        restart_timeout=5,
        restart_grace=3,
        rcon_fail_threshold=3,
        empty_confirm_seconds=1,
        rcon_timeout=1.0,
        config_dir=Path("config"),
        health_state_path=Path("health.json"),
        log_level="INFO",
    )
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]
