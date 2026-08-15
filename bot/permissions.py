from __future__ import annotations

from bot.config import ConfigStore, GuildPermissions
from bot.constants import DEFAULT_MIN_TIER, Tier


def resolve_tier(guild: GuildPermissions, role_ids: set[str]) -> Tier:
    if role_ids & guild.admin_role_ids:
        return Tier.A
    if role_ids & guild.member_role_ids:
        return Tier.B
    return Tier.C


def min_tier_for(guild: GuildPermissions, command_key: str) -> Tier:
    if command_key in guild.command_min_tier:
        return guild.command_min_tier[command_key]
    return DEFAULT_MIN_TIER[command_key]


def can_run(guild: GuildPermissions, role_ids: set[str], command_key: str) -> bool:
    return resolve_tier(guild, role_ids) >= min_tier_for(guild, command_key)


def can_cancel(
    actor_id: int,
    actor_tier: Tier,
    owner_id: int,
) -> bool:
    if actor_tier >= Tier.A:
        return True
    return actor_tier >= Tier.B and actor_id == owner_id


def channel_allowed(guild: GuildPermissions, channel_id: int | None) -> bool:
    if not guild.command_channel_ids:
        return True
    if channel_id is None:
        return False
    return str(channel_id) in guild.command_channel_ids


def is_break_glass(guild: GuildPermissions, user_id: int) -> bool:
    return str(user_id) in guild.break_glass_user_ids


def access_change_allowed(
    guild: GuildPermissions,
    user_id: int,
    *,
    target_is_admin: bool,
) -> bool:
    if not target_is_admin:
        return True
    return is_break_glass(guild, user_id)


class PermissionGate:
    def __init__(self, store: ConfigStore) -> None:
        self.store = store

    def guild(self, guild_id: int | str) -> GuildPermissions | None:
        return self.store.permissions.get(guild_id)
