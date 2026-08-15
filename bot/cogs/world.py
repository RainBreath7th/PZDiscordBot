from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.constants import (
    COMMAND_GIVE,
    COMMAND_HORDE,
    COMMAND_PLAYER,
    COMMAND_TELEPORT,
    COMMAND_WEATHER,
)
from bot.discord_util import (
    command_guard,
    player_autocomplete,
    pz_bot,
    reject_range,
    reply_key,
    resolve_online_player,
)


class WorldCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    teleport = app_commands.Group(name="teleport", description="Teleport a player.")
    give = app_commands.Group(name="give", description="Give items, XP, or a vehicle.")
    player = app_commands.Group(name="player", description="Toggle player flags.")
    weather = app_commands.Group(name="weather", description="Trigger world events.")

    @teleport.command(name="to-player", description="Teleport a player to another player.")
    @app_commands.autocomplete(player=player_autocomplete, target=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_TELEPORT)
    async def teleport_to_player(
        self,
        interaction: discord.Interaction,
        player: str,
        target: str,
    ) -> None:
        bot = pz_bot(interaction)
        src = await resolve_online_player(interaction, bot, player)
        dst = await resolve_online_player(interaction, bot, target)
        if src is None or dst is None:
            return
        await bot.rcon.teleport(src, dst)
        await reply_key(
            interaction, bot, "teleport.to_player", ephemeral=True, player=src, target=dst
        )

    @teleport.command(name="to-coords", description="Teleport a player to coordinates.")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_TELEPORT)
    async def teleport_to_coords(
        self,
        interaction: discord.Interaction,
        player: str,
        x: int,
        y: int,
        z: int,
    ) -> None:
        bot = pz_bot(interaction)
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        await bot.rcon.teleportto(name, x, y, z)
        await reply_key(
            interaction,
            bot,
            "teleport.to_coords",
            ephemeral=True,
            player=name,
            x=x,
            y=y,
            z=z,
        )

    @give.command(name="item", description="Give an item script to a player.")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_GIVE)
    async def give_item(
        self,
        interaction: discord.Interaction,
        player: str,
        item: str,
        count: int = 1,
    ) -> None:
        bot = pz_bot(interaction)
        limits = bot.store.limits.item_count
        if await reject_range(interaction, bot, count, limits.minimum, limits.maximum, "item"):
            return
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        await bot.rcon.additem(name, item, count)
        await reply_key(
            interaction,
            bot,
            "give.item",
            ephemeral=True,
            player=name,
            item=item,
            count=count,
        )

    @give.command(name="xp", description="Give perk XP to a player.")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_GIVE)
    async def give_xp(
        self,
        interaction: discord.Interaction,
        player: str,
        perk: str,
        amount: int,
    ) -> None:
        bot = pz_bot(interaction)
        limits = bot.store.limits.xp
        if await reject_range(interaction, bot, amount, limits.minimum, limits.maximum, "xp"):
            return
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        await bot.rcon.addxp(name, perk, amount)
        await reply_key(
            interaction,
            bot,
            "give.xp",
            ephemeral=True,
            player=name,
            perk=perk,
            amount=amount,
        )

    @give.command(name="vehicle", description="Spawn a vehicle near a player.")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_GIVE)
    async def give_vehicle(
        self,
        interaction: discord.Interaction,
        player: str,
        script: str,
    ) -> None:
        bot = pz_bot(interaction)
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        await bot.rcon.addvehicle(script, name)
        await reply_key(
            interaction,
            bot,
            "give.vehicle",
            ephemeral=True,
            player=name,
            script=script,
        )

    @app_commands.command(name="horde", description="Spawn a horde near a player.")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_HORDE)
    async def horde(
        self,
        interaction: discord.Interaction,
        player: str,
        count: int,
    ) -> None:
        bot = pz_bot(interaction)
        limits = bot.store.limits.horde
        if await reject_range(interaction, bot, count, limits.minimum, limits.maximum, "horde"):
            return
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        await bot.rcon.createhorde(count, name)
        await reply_key(
            interaction, bot, "horde.done", ephemeral=True, player=name, count=count
        )

    @player.command(name="god", description="Toggle godmode.")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_PLAYER)
    async def player_god(self, interaction: discord.Interaction, player: str) -> None:
        bot = pz_bot(interaction)
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        await bot.rcon.godmode(name)
        await reply_key(interaction, bot, "player.god", ephemeral=True, player=name)

    @player.command(name="invisible", description="Toggle invisibility.")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_PLAYER)
    async def player_invisible(self, interaction: discord.Interaction, player: str) -> None:
        bot = pz_bot(interaction)
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        await bot.rcon.invisible(name)
        await reply_key(interaction, bot, "player.invisible", ephemeral=True, player=name)

    @player.command(name="noclip", description="Toggle noclip.")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.guild_only()
    @command_guard(COMMAND_PLAYER)
    async def player_noclip(self, interaction: discord.Interaction, player: str) -> None:
        bot = pz_bot(interaction)
        name = await resolve_online_player(interaction, bot, player)
        if name is None:
            return
        await bot.rcon.noclip(name)
        await reply_key(interaction, bot, "player.noclip", ephemeral=True, player=name)

    @weather.command(name="start-rain", description="Start rain.")
    @app_commands.guild_only()
    @command_guard(COMMAND_WEATHER)
    async def weather_start_rain(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        await bot.rcon.startrain()
        await reply_key(interaction, bot, "weather.start_rain", ephemeral=True)

    @weather.command(name="stop-rain", description="Stop rain.")
    @app_commands.guild_only()
    @command_guard(COMMAND_WEATHER)
    async def weather_stop_rain(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        await bot.rcon.stoprain()
        await reply_key(interaction, bot, "weather.stop_rain", ephemeral=True)

    @weather.command(name="thunder", description="Trigger thunder.")
    @app_commands.guild_only()
    @command_guard(COMMAND_WEATHER)
    async def weather_thunder(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        await bot.rcon.thunder()
        await reply_key(interaction, bot, "weather.thunder", ephemeral=True)

    @weather.command(name="chopper", description="Trigger a helicopter event.")
    @app_commands.guild_only()
    @command_guard(COMMAND_WEATHER)
    async def weather_chopper(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        await bot.rcon.chopper()
        await reply_key(interaction, bot, "weather.chopper", ephemeral=True)

    @weather.command(name="gunshot", description="Trigger a gunshot event.")
    @app_commands.guild_only()
    @command_guard(COMMAND_WEATHER)
    async def weather_gunshot(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        await bot.rcon.gunshot()
        await reply_key(interaction, bot, "weather.gunshot", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WorldCog(bot))
