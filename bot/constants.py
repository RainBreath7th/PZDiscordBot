"""Shared constants. Command keys are the permissions.yaml override names."""

from enum import IntEnum

SUPPORTED_LOCALES = ("zh", "en", "jp")
PLACEHOLDER_GUILD_ID = "000000000000000000"

ACCESS_LEVELS = ("none", "observer", "gm", "overseer", "moderator", "admin")


class Tier(IntEnum):
    C = 0
    B = 1
    A = 2


COMMAND_PLAYERS = "players"
COMMAND_RESTART_QUEUE = "restart_queue"
COMMAND_RESTART_CANCEL = "restart_cancel"
COMMAND_RESTART_STATUS = "restart_status"
COMMAND_RESTART_NOW = "restart_now"
COMMAND_ANNOUNCE = "announce"
COMMAND_SAVE = "save"
COMMAND_KICK = "kick"
COMMAND_BAN = "ban"
COMMAND_UNBAN = "unban"
COMMAND_WHITELIST = "whitelist"
COMMAND_ACCESS = "access"
COMMAND_TELEPORT = "teleport"
COMMAND_GIVE = "give"
COMMAND_HORDE = "horde"
COMMAND_PLAYER = "player"
COMMAND_WEATHER = "weather"

DEFAULT_MIN_TIER: dict[str, Tier] = {
    COMMAND_PLAYERS: Tier.C,
    COMMAND_RESTART_QUEUE: Tier.B,
    COMMAND_RESTART_CANCEL: Tier.B,
    COMMAND_RESTART_STATUS: Tier.B,
    COMMAND_RESTART_NOW: Tier.A,
    COMMAND_ANNOUNCE: Tier.A,
    COMMAND_SAVE: Tier.A,
    COMMAND_KICK: Tier.A,
    COMMAND_BAN: Tier.A,
    COMMAND_UNBAN: Tier.A,
    COMMAND_WHITELIST: Tier.A,
    COMMAND_ACCESS: Tier.A,
    COMMAND_TELEPORT: Tier.A,
    COMMAND_GIVE: Tier.A,
    COMMAND_HORDE: Tier.A,
    COMMAND_PLAYER: Tier.A,
    COMMAND_WEATHER: Tier.A,
}

QUERY_COMMANDS = frozenset({COMMAND_PLAYERS, COMMAND_RESTART_STATUS})
RESTART_SAFE_COMMANDS = frozenset({COMMAND_RESTART_STATUS})
