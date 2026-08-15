from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.constants import COMMAND_PLAYERS
from bot.discord_util import command_guard, pz_bot, reply_key


class PlayersCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="players", description="Show who is online on the PZ server.")
    @app_commands.guild_only()
    @command_guard(COMMAND_PLAYERS)
    async def players(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        listing = await bot.rcon.players()
        bot.players_cache.update(listing)
        if listing.count == 0 or not listing.names:
            await reply_key(
                interaction,
                bot,
                "players.empty",
                ephemeral=False,
                title_key="players.title",
            )
            return
        names = ", ".join(listing.names)
        embed = discord.Embed(
            title=bot.translator.render("en", "players.title"),
            colour=discord.Colour.dark_grey(),
        )
        for locale, label in (
            ("zh", "中文"),
            ("en", "English"),
            ("jp", "日本語"),
        ):
            if locale not in bot.store.i18n.discord_locales:
                continue
            count_line = bot.translator.render(locale, "players.count", count=listing.count)
            list_line = bot.translator.render(locale, "players.list", names=names)
            embed.add_field(name=label, value=f"{count_line}\n{list_line}", inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlayersCog(bot))
