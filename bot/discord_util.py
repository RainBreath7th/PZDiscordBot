from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

import discord
from discord import app_commands

from bot.constants import QUERY_COMMANDS, RESTART_SAFE_COMMANDS, Tier
from bot.permissions import (
    can_run,
    channel_allowed,
    resolve_tier,
)
from bot.rcon_client import RconError

if TYPE_CHECKING:
    from bot.app import PZBot


LOCALE_LABELS = {"zh": "中文", "en": "English", "jp": "日本語"}


@dataclass
class GateOK:
    tier: Tier
    guild_id: int


class GateDenied(Exception):
    def __init__(self, key: str, **kwargs: object) -> None:
        super().__init__(key)
        self.key = key
        self.kwargs = kwargs


def build_locale_embed(
    bot: PZBot,
    key: str,
    *,
    title_key: str | None = None,
    **kwargs: object,
) -> discord.Embed:
    title = bot.translator.render("en", title_key) if title_key else None
    embed = discord.Embed(title=title, colour=discord.Colour.dark_grey())
    for locale, text in bot.translator.discord_lines(key, **kwargs):
        label = LOCALE_LABELS.get(locale, locale)
        value = text if len(text) <= 1024 else text[:1021] + "..."
        embed.add_field(name=label, value=value or "-", inline=False)
    return embed


async def reply_key(
    interaction: discord.Interaction,
    bot: PZBot,
    key: str,
    *,
    ephemeral: bool,
    title_key: str | None = None,
    **kwargs: object,
) -> None:
    embed = build_locale_embed(bot, key, title_key=title_key, **kwargs)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


def pz_bot(interaction: discord.Interaction) -> PZBot:
    return interaction.client  # type: ignore[return-value]


async def gate(interaction: discord.Interaction, command_key: str) -> GateOK:
    bot = pz_bot(interaction)
    bot.store.reload_if_changed()
    if interaction.guild is None or interaction.guild_id is None:
        raise GateDenied("error.not_in_guild")
    guild = bot.gate.guild(interaction.guild_id)
    if guild is None:
        raise GateDenied("error.unknown_guild")
    if not channel_allowed(guild, interaction.channel_id):
        raise GateDenied("error.wrong_channel")
    role_ids = {str(role.id) for role in getattr(interaction.user, "roles", [])}
    if not can_run(guild, role_ids, command_key):
        raise GateDenied("error.insufficient_tier")
    if (
        command_key not in RESTART_SAFE_COMMANDS
        and bot.queue.in_restarting_window()
    ):
        snap = bot.queue.snapshot()
        raise GateDenied(
            "error.restarting",
            seconds=snap.grace_remaining(bot.queue.now()),
        )
    return GateOK(
        tier=resolve_tier(guild, role_ids),
        guild_id=interaction.guild_id,
    )


F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


def command_guard(command_key: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(self: Any, interaction: discord.Interaction, *args: Any, **kwargs: Any):
            bot = pz_bot(interaction)
            ephemeral = command_key not in QUERY_COMMANDS
            try:
                await gate(interaction, command_key)
            except GateDenied as denied:
                await reply_key(
                    interaction,
                    bot,
                    denied.key,
                    ephemeral=True,
                    **denied.kwargs,
                )
                return None
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=ephemeral)
            try:
                return await func(self, interaction, *args, **kwargs)
            except RconError as exc:
                await reply_key(
                    interaction,
                    bot,
                    "error.rcon_failed",
                    ephemeral=True,
                    detail=str(exc),
                )
                return None

        return wrapper  # type: ignore[return-value]

    return decorator


class ConfirmView(discord.ui.View):
    def __init__(self, owner_id: int, timeout: float) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.result: asyncio.Future[bool] = asyncio.get_running_loop().create_future()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        bot = pz_bot(interaction)
        await reply_key(interaction, bot, "error.not_your_confirm", ephemeral=True)
        return False

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        if not self.result.done():
            self.result.set_result(True)
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        if not self.result.done():
            self.result.set_result(False)
        await interaction.response.defer()
        self.stop()

    async def on_timeout(self) -> None:
        if not self.result.done():
            self.result.set_result(False)


async def ask_confirm(
    interaction: discord.Interaction,
    bot: PZBot,
    body_key: str,
    **kwargs: object,
) -> bool:
    view = ConfirmView(
        owner_id=interaction.user.id,
        timeout=float(bot.store.limits.confirm_timeout_seconds),
    )
    embed = build_locale_embed(bot, body_key, title_key="confirm.title", **kwargs)
    try:
        await interaction.edit_original_response(embed=embed, view=view)
    except discord.HTTPException:
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    try:
        confirmed = await view.result
    finally:
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        try:
            await interaction.edit_original_response(view=view)
        except discord.HTTPException:
            pass
    if not confirmed:
        await reply_key(interaction, bot, "error.cancelled", ephemeral=True)
    return confirmed


async def player_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    bot = pz_bot(interaction)
    needle = current.casefold()
    choices: list[app_commands.Choice[str]] = []
    for name in bot.players_cache.names():
        if needle and needle not in name.casefold():
            continue
        choices.append(app_commands.Choice(name=name, value=name))
        if len(choices) >= 25:
            break
    return choices


async def resolve_online_player(
    interaction: discord.Interaction,
    bot: PZBot,
    typed: str,
) -> str | None:
    try:
        listing = await bot.rcon.players()
        bot.players_cache.update(listing)
    except RconError as exc:
        await reply_key(
            interaction,
            bot,
            "error.rcon_failed",
            ephemeral=True,
            detail=str(exc),
        )
        return None
    resolved = bot.players_cache.resolve(typed)
    if isinstance(resolved, str):
        return resolved
    if not resolved:
        await reply_key(
            interaction,
            bot,
            "error.unknown_player",
            ephemeral=True,
            name=typed,
        )
        return None
    await reply_key(
        interaction,
        bot,
        "error.ambiguous_player",
        ephemeral=True,
        names=", ".join(resolved),
    )
    return None


async def reject_range(
    interaction: discord.Interaction,
    bot: PZBot,
    value: int,
    minimum: int,
    maximum: int,
    what: str,
) -> bool:
    """Return True when the value is out of range and a reply was sent."""
    if minimum <= value <= maximum:
        return False
    await reply_key(
        interaction,
        bot,
        "error.limit_exceeded",
        ephemeral=True,
        what=what,
        min=minimum,
        max=maximum,
    )
    return True
