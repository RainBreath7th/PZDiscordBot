from __future__ import annotations

from pathlib import Path

from bot.config import load_yaml_bundle
from bot.constants import PLACEHOLDER_GUILD_ID


def test_shipped_config_loads() -> None:
    loaded = load_yaml_bundle(Path("config"))
    assert PLACEHOLDER_GUILD_ID in loaded.permissions.guilds
    assert loaded.i18n.discord_locales == ("zh", "en", "jp")
    assert loaded.limits.horde.maximum == 50
    assert "queued" in loaded.locales["zh"]["restart"]
