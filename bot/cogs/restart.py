from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.constants import (
    COMMAND_RESTART_CANCEL,
    COMMAND_RESTART_NOW,
    COMMAND_RESTART_QUEUE,
    COMMAND_RESTART_STATUS,
    Tier,
)
from bot.discord_util import ask_confirm, command_guard, pz_bot, reply_key
from bot.permissions import can_cancel
from bot.restart_queue import QueueState


class RestartCog(commands.GroupCog, group_name="restart"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="queue", description="Queue a restart when the server is empty.")
    @app_commands.guild_only()
    @command_guard(COMMAND_RESTART_QUEUE)
    async def queue(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        existing = await bot.queue.enqueue(interaction.user.id, interaction.user.display_name)
        if existing is not None:
            await reply_key(
                interaction,
                bot,
                "restart.already_queued",
                ephemeral=True,
                name=existing.owner_name or "?",
                elapsed=existing.elapsed(bot.queue.now()),
                remaining=existing.remaining(bot.queue.now()),
            )
            return
        try:
            for message in bot.translator.game_messages("restart.queued_ingame"):
                await bot.rcon.servermsg(message)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("queued in-game announce failed")
        await reply_key(
            interaction,
            bot,
            "restart.queued",
            ephemeral=True,
            timeout=bot.settings.restart_timeout,
        )

    @app_commands.command(name="cancel", description="Cancel a queued restart.")
    @app_commands.guild_only()
    @command_guard(COMMAND_RESTART_CANCEL)
    async def cancel(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        snap = bot.queue.snapshot()
        if snap.state != QueueState.QUEUED or snap.owner_id is None:
            await reply_key(interaction, bot, "restart.nothing_to_cancel", ephemeral=True)
            return
        guild = bot.gate.guild(interaction.guild_id or 0)
        role_ids = {str(role.id) for role in getattr(interaction.user, "roles", [])}
        actor_tier = Tier.C
        if guild is not None:
            from bot.permissions import resolve_tier

            actor_tier = resolve_tier(guild, role_ids)
        if not can_cancel(interaction.user.id, actor_tier, snap.owner_id):
            await reply_key(interaction, bot, "restart.cancel_denied", ephemeral=True)
            return
        ok, after = await bot.queue.cancel(
            interaction.user.id, as_admin=actor_tier >= Tier.A
        )
        if not ok:
            await reply_key(interaction, bot, "restart.cancel_denied", ephemeral=True)
            return
        if after.owner_id == interaction.user.id:
            await reply_key(interaction, bot, "restart.cancelled_own", ephemeral=True)
        else:
            await reply_key(
                interaction,
                bot,
                "restart.cancelled_other",
                ephemeral=True,
                name=after.owner_name or "?",
            )

    @app_commands.command(name="status", description="Show the restart queue or restarting window.")
    @app_commands.guild_only()
    @command_guard(COMMAND_RESTART_STATUS)
    async def status(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        snap = bot.queue.snapshot()
        now = bot.queue.now()
        if snap.state == QueueState.QUEUED:
            await reply_key(
                interaction,
                bot,
                "restart.status_queued",
                ephemeral=False,
                name=snap.owner_name or "?",
                elapsed=snap.elapsed(now),
                remaining=snap.remaining(now),
            )
            return
        if snap.state == QueueState.RESTARTING:
            await reply_key(
                interaction,
                bot,
                "restart.status_restarting",
                ephemeral=False,
                seconds=snap.grace_remaining(now),
            )
            return
        await reply_key(interaction, bot, "restart.status_idle", ephemeral=False)

    @app_commands.command(name="now", description="Force save and quit immediately.")
    @app_commands.guild_only()
    @command_guard(COMMAND_RESTART_NOW)
    async def now(self, interaction: discord.Interaction) -> None:
        bot = pz_bot(interaction)
        if not await ask_confirm(interaction, bot, "confirm.now"):
            return
        reason = await bot.queue.force_now(interaction.user.id, interaction.user.display_name)
        if reason == "already_restarting":
            snap = bot.queue.snapshot()
            await reply_key(
                interaction,
                bot,
                "error.restarting",
                ephemeral=True,
                seconds=snap.grace_remaining(bot.queue.now()),
            )
            return
        if reason is None:
            await reply_key(interaction, bot, "restart.now_started", ephemeral=True)
            return
        key = {
            "save_failed": "restart.save_failed",
            "quit_failed": "restart.quit_failed",
        }.get(reason.value, "restart.now_started")
        await reply_key(interaction, bot, key, ephemeral=True, detail=reason.value)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RestartCog(bot))
