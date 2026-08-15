from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.config import ConfigStore
from bot.health import HealthState
from bot.i18n import Translator
from bot.logging_setup import setup_logging
from bot.permissions import PermissionGate
from bot.players import PlayerCache
from bot.rcon_client import RconClient
from bot.restart_queue import RestartQueue
from bot.settings import Settings

log = logging.getLogger(__name__)


class PZBot(commands.Bot):
    def __init__(self, settings: Settings, store: ConfigStore) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.store = store
        self.translator = Translator(store)
        self.gate = PermissionGate(store)
        self.rcon = RconClient(settings)
        self.players_cache = PlayerCache()
        self.health = HealthState(settings.health_state_path, reset=True)
        self.queue = RestartQueue(
            settings,
            self.rcon,
            announce=self._announce_ingame,
            notify=self._notify_owner,
            on_window=self._on_window,
        )

    async def setup_hook(self) -> None:
        await self.load_extension("bot.cogs.players")
        await self.load_extension("bot.cogs.restart")
        await self.load_extension("bot.cogs.ops")
        await self.load_extension("bot.cogs.session")
        await self.load_extension("bot.cogs.world")
        guild_ids = self.store.syncable_guild_ids()
        if not guild_ids:
            log.warning("no real guild ids in permissions.yaml; slash sync skipped")
            return
        for guild_id in guild_ids:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info(
                "synced slash commands",
                extra={"guild_id": guild_id, "detail": str(len(synced))},
            )
        # Commands stay guild-scoped. Wipe any leftover global slash set.
        self.tree.clear_commands(guild=None)
        await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("bot ready", extra={"detail": str(self.user)})

    async def _announce_ingame(self, key: str) -> None:
        for message in self.translator.game_messages(key):
            await self.rcon.servermsg(message)

    async def _notify_owner(self, user_id: int, key: str, kwargs: dict[str, object]) -> None:
        from bot.discord_util import build_locale_embed

        user = self.get_user(user_id) or await self.fetch_user(user_id)
        embed = build_locale_embed(self, key, **kwargs)
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            log.info("owner DM failed", extra={"operator": user_id, "detail": key})

    def _on_window(self, until: float) -> None:
        self.health.write(restarting_until=until)


def run() -> None:
    settings = Settings.from_env()
    setup_logging(settings.log_level)
    store = ConfigStore(settings.config_dir)
    bot = PZBot(settings, store)
    bot.run(settings.discord_token, log_handler=None)


