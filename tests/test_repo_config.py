from __future__ import annotations

from pathlib import Path

import yaml

from bot.config import load_yaml_bundle
from bot.constants import PLACEHOLDER_GUILD_ID

ROOT = Path(__file__).resolve().parents[1]


def test_shipped_config_loads() -> None:
    loaded = load_yaml_bundle(Path("config"))
    assert PLACEHOLDER_GUILD_ID in loaded.permissions.guilds
    assert loaded.i18n.discord_locales == ("zh", "en", "jp")
    assert loaded.limits.horde.maximum == 50
    assert "queued" in loaded.locales["zh"]["restart"]


def _load_compose(name: str) -> dict:
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def _assert_shared_bot_service(service: dict) -> None:
    assert service["image"] == "pz-discord-bot:latest"
    assert service["restart"] == "unless-stopped"
    env = service["environment"]
    for key in ("DISCORD_TOKEN", "RCON_HOST", "RCON_PORT", "RCON_PASSWORD"):
        assert key in env
    assert service["healthcheck"]["test"] == ["CMD", "python", "-m", "bot.health"]
    assert service["logging"]["options"]["max-size"] == "10m"
    assert "./config:/app/config" in service["volumes"]
    assert "docker.sock" not in str(service).lower()


def test_compose_same_host_joins_external_network() -> None:
    data = _load_compose("compose.bot.yaml")
    service = data["services"]["pz-bot"]
    _assert_shared_bot_service(service)
    assert "networks" in service
    assert data["networks"]["pz-net"]["external"] is True
    assert "BOT_NETWORK" in data["networks"]["pz-net"]["name"]
    assert "ports" not in service


def test_compose_remote_has_no_docker_network() -> None:
    data = _load_compose("compose.bot.remote.yaml")
    service = data["services"]["pz-bot"]
    _assert_shared_bot_service(service)
    assert "networks" not in data
    assert "networks" not in service
    assert "ports" not in service


def test_compose_native_reaches_host() -> None:
    data = _load_compose("compose.bot.native.yaml")
    service = data["services"]["pz-bot"]
    _assert_shared_bot_service(service)
    assert "host.docker.internal:host-gateway" in service["extra_hosts"]
    assert "networks" not in data
    assert "ports" not in service
