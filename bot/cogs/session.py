from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.constants import (
    ACCESS_LEVELS,
    COMMAND_ACCESS,
    COMMAND_BAN,
    COMMAND_KICK,
    COMMAND_UNBAN,
    COMMAND_WHITELIST,
)
from bot.discord_util import (
    ask_confirm,
    command_guard,
    player_autocomplete,
    pz_bot,
    reply_key,
    resolve_online_player,
)
from bot.permissions import access_change_allowed


class SessionCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="kick", description="Kick an online player.")
    @app_commands.describe(player="Character name", reason="Optional kick reason")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_KICK)
    async def kick(
        self,
        interaction: discord.Interaction,
        player: str,
        reason: str = "",
    ) -> None:
        bot = pz_bot(interaction)
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        if not await ask_confirm(interaction, bot, "confirm.kick", player=name, reason=reason or "-"):
            return
        await bot.rcon.kickuser(name, reason)
        await reply_key(interaction, bot, "kick.done", ephemeral=True, player=name)

    ban_group = app_commands.Group(name="ban", description="Ban a user or SteamID.")
    unban_group = app_commands.Group(name="unban", description="Unban a user or SteamID.")
    whitelist_group = app_commands.Group(name="whitelist", description="Manage the whitelist.")
    access_group = app_commands.Group(name="access", description="Change in-game access level.")

    @ban_group.command(name="user", description="Ban by character name.")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_BAN)
    async def ban_user(self, interaction: discord.Interaction, player: str) -> None:
        bot = pz_bot(interaction)
        if not await ask_confirm(interaction, bot, "confirm.ban_user", player=player):
            return
        await bot.rcon.banuser(player)
        await reply_key(interaction, bot, "ban.done_user", ephemeral=True, player=player)

    @ban_group.command(name="steamid", description="Ban by SteamID.")
    @app_commands.guild_only()
    @command_guard(COMMAND_BAN)
    async def ban_steamid(self, interaction: discord.Interaction, steamid: str) -> None:
        bot = pz_bot(interaction)
        if not await ask_confirm(interaction, bot, "confirm.ban_steamid", steamid=steamid):
            return
        await bot.rcon.banid(steamid)
        await reply_key(interaction, bot, "ban.done_steamid", ephemeral=True, steamid=steamid)

    @unban_group.command(name="user", description="Unban by character name.")
    @app_commands.guild_only()
    @command_guard(COMMAND_UNBAN)
    async def unban_user(self, interaction: discord.Interaction, player: str) -> None:
        bot = pz_bot(interaction)
        if not await ask_confirm(interaction, bot, "confirm.unban_user", player=player):
            return
        await bot.rcon.unbanuser(player)
        await reply_key(interaction, bot, "unban.done_user", ephemeral=True, player=player)

    @unban_group.command(name="steamid", description="Unban by SteamID.")
    @app_commands.guild_only()
    @command_guard(COMMAND_UNBAN)
    async def unban_steamid(self, interaction: discord.Interaction, steamid: str) -> None:
        bot = pz_bot(interaction)
        if not await ask_confirm(interaction, bot, "confirm.unban_steamid", steamid=steamid):
            return
        await bot.rcon.unbanid(steamid)
        await reply_key(interaction, bot, "unban.done_steamid", ephemeral=True, steamid=steamid)

    @whitelist_group.command(name="add", description="Add a user to the whitelist.")
    @app_commands.describe(player="Account name", password="Whitelist password")
    @app_commands.guild_only()
    @command_guard(COMMAND_WHITELIST)
    async def whitelist_add(
        self,
        interaction: discord.Interaction,
        player: str,
        password: str,
    ) -> None:
        bot = pz_bot(interaction)
        await bot.rcon.adduser(player, password)
        await reply_key(interaction, bot, "whitelist.added", ephemeral=True, player=player)

    @whitelist_group.command(name="remove", description="Remove a user from the whitelist.")
    @app_commands.guild_only()
    @command_guard(COMMAND_WHITELIST)
    async def whitelist_remove(self, interaction: discord.Interaction, player: str) -> None:
        bot = pz_bot(interaction)
        if not await ask_confirm(interaction, bot, "confirm.whitelist_remove", player=player):
            return
        await bot.rcon.removeuserfromwhitelist(player)
        await reply_key(interaction, bot, "whitelist.removed", ephemeral=True, player=player)

    @access_group.command(name="set", description="Set a player's in-game access level.")
    @app_commands.describe(player="Character name", level="PZ access level")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.choices(
        level=[app_commands.Choice(name=item, value=item) for item in ACCESS_LEVELS]
    )
    @app_commands.guild_only()
    @command_guard(COMMAND_ACCESS)
    async def access_set(
        self,
        interaction: discord.Interaction,
        player: str,
        level: app_commands.Choice[str],
    ) -> None:
        bot = pz_bot(interaction)
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        guild = bot.gate.guild(interaction.guild_id or 0)
        if guild is None:
            await reply_key(interaction, bot, "error.unknown_guild", ephemeral=True)
            return
        # RCON cannot tell us the current access level. Treat any change
        # that is not a promotion to admin as touching a possible admin.
        changing_possible_admin = level.value != "admin"
        if not access_change_allowed(
            guild,
            interaction.user.id,
            target_is_admin=changing_possible_admin,
        ):
            await reply_key(interaction, bot, "error.break_glass_required", ephemeral=True)
            return
        if not await ask_confirm(
            interaction, bot, "confirm.access", player=name, level=level.value
        ):
            return
        await bot.rcon.setaccesslevel(name, level.value)
        await reply_key(
            interaction, bot, "access.done", ephemeral=True, player=name, level=level.value
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SessionCog(bot))
