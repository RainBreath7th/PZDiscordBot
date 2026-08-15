from __future__ import annotations

from pathlib import Path

import pytest

from bot.config import ConfigStore, load_yaml_bundle
from bot.settings import ConfigError, Settings


def test_hot_reload_keeps_last_good(store, config_dir: Path) -> None:
    original = store.permissions.get("111")
    assert original is not None
    (config_dir / "permissions.yaml").write_text("guilds: [broken", encoding="utf-8")
    assert store.reload_if_changed() is False
    assert store.permissions.get("111") is original


def test_startup_rejects_bad_yaml(config_dir: Path) -> None:
    (config_dir / "i18n.yaml").write_text("discord_locales: [nope]\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_yaml_bundle(config_dir)


def test_settings_require_rcon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("RCON_HOST", raising=False)
    monkeypatch.delenv("RCON_PORT", raising=False)
    monkeypatch.delenv("RCON_PASSWORD", raising=False)
    with pytest.raises(ConfigError):
        Settings.from_env()
    monkeypatch.setenv("DISCORD_TOKEN", "t")
    monkeypatch.setenv("RCON_HOST", "pz")
    monkeypatch.setenv("RCON_PORT", "27015")
    monkeypatch.setenv("RCON_PASSWORD", "pw")
    settings = Settings.from_env()
    assert settings.rcon_host == "pz"
    assert settings.restart_grace == 360
