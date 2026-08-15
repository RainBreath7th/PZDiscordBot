from __future__ import annotations

from bot.constants import COMMAND_ANNOUNCE, COMMAND_PLAYERS, COMMAND_RESTART_QUEUE, Tier
from bot.permissions import (
    access_change_allowed,
    can_cancel,
    can_run,
    channel_allowed,
    min_tier_for,
    resolve_tier,
)


def test_highest_role_wins(store) -> None:
    guild = store.permissions.get("111")
    assert guild is not None
    assert resolve_tier(guild, {"20"}) is Tier.B
    assert resolve_tier(guild, {"10", "20"}) is Tier.A
    assert resolve_tier(guild, {"999"}) is Tier.C


def test_default_and_override_min_tier(store, config_dir) -> None:
    guild = store.permissions.get("111")
    assert guild is not None
    assert min_tier_for(guild, COMMAND_PLAYERS) is Tier.C
    assert min_tier_for(guild, COMMAND_ANNOUNCE) is Tier.A
    assert can_run(guild, {"20"}, COMMAND_RESTART_QUEUE)
    assert not can_run(guild, {"20"}, COMMAND_ANNOUNCE)

    text = (config_dir / "permissions.yaml").read_text(encoding="utf-8")
    (config_dir / "permissions.yaml").write_text(
        text.replace("command_min_tier: {}", "command_min_tier: {announce: B}"),
        encoding="utf-8",
    )
    assert store.reload_if_changed()
    guild = store.permissions.get("111")
    assert guild is not None
    assert can_run(guild, {"20"}, COMMAND_ANNOUNCE)


def test_cancel_own_versus_admin() -> None:
    assert can_cancel(1, Tier.B, 1)
    assert not can_cancel(2, Tier.B, 1)
    assert can_cancel(2, Tier.A, 1)
    assert not can_cancel(1, Tier.C, 1)


def test_channel_whitelist_and_break_glass(store) -> None:
    guild = store.permissions.get("111")
    assert guild is not None
    assert channel_allowed(guild, 123)
    assert access_change_allowed(guild, 1, target_is_admin=False)
    assert not access_change_allowed(guild, 1, target_is_admin=True)
    assert access_change_allowed(guild, 99, target_is_admin=True)
