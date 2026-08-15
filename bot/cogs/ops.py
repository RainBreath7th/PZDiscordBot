from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.constants import COMMAND_ANNOUNCE, COMMAND_SAVE
from bot.discord_util import command_guard, pz_bot, reply_key
from bot.rcon_client import RconError


class OpsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="announce", description="Broadcast a message in-game.")
    @app_commands.describe(message="Text sent as-is for each configured GameLocale.")
    @app_commands.guild_only()
    @command_guard(COMMAND_ANNOUNCE)
    async def announce(self, interaction: discord.Interaction, message: str) -> None:
        bot = pz_bot(interaction)
        for line in bot.translator.passthrough_game_messages(message):
            await bot.rcon.servermsg(line)
        await reply_key(interaction, bot, "announce.sent", ephemeral=True)

    @app_commands.command(name="save", description="Save the PZ world without restarting.")
    @app_commands.guild_only()
    @command_guard(COMMAND_SAVE)
    async def save(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        try:
            await bot.rcon.save()
        except RconError as exc:
            await reply_key(interaction, bot, "save.failed", ephemeral=True, detail=str(exc))
            return
        await reply_key(interaction, bot, "save.ok", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OpsCog(bot))
