from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from bot.settings import Settings

log = logging.getLogger(__name__)

_COUNT_RE = re.compile(r"\((\d+)\)")
_NAME_LINE_RE = re.compile(r"^\s*[-*]?\s*(.+?)\s*$")


class RconError(Exception):
    """RCON transport or protocol failure."""


@dataclass(frozen=True)
class PlayerList:
    count: int
    names: tuple[str, ...]


def parse_players(raw: str) -> PlayerList:
    """Parse the text returned by PZ `players`. Not JSON."""
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line for line in text.split("\n") if line.strip()]
    names: list[str] = []
    declared: int | None = None
    for line in lines:
        match = _COUNT_RE.search(line)
        if match and declared is None and "player" in line.lower():
            declared = int(match.group(1))
            continue
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith("players") or lowered.startswith("connected"):
            continue
        name_match = _NAME_LINE_RE.match(stripped)
        if not name_match:
            continue
        name = name_match.group(1).strip().strip('"')
        if not name or name.lower() in {"none", "no players"}:
            continue
        names.append(name)
    unique: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(name)
    count = declared if declared is not None else len(unique)
    return PlayerList(count=count, names=tuple(unique))


def quote_arg(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    if any(ch.isspace() for ch in value) or not value:
        return f'"{escaped}"'
    return escaped


class RconClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def run(self, command: str) -> str:
        try:
            from rcon.source import rcon as source_rcon
        except ImportError as exc:  # pragma: no cover - import guard
            raise RconError("rcon package is not installed") from exc
        log.info("rcon send", extra={"rcon_cmd": command.split(" ", 1)[0]})
        try:
            response = await source_rcon(
                command,
                host=self._settings.rcon_host,
                port=self._settings.rcon_port,
                passwd=self._settings.rcon_password,
                timeout=self._settings.rcon_timeout,
            )
        except Exception as exc:
            raise RconError(str(exc) or exc.__class__.__name__) from exc
        return "" if response is None else str(response)

    async def players(self) -> PlayerList:
        raw = await self.run("players")
        return parse_players(raw)

    async def servermsg(self, message: str) -> str:
        return await self.run(f"servermsg {quote_arg(message)}")

    async def save(self) -> str:
        return await self.run("save")

    async def quit(self) -> str:
        return await self.run("quit")

    async def kickuser(self, player: str, reason: str = "") -> str:
        cmd = f"kickuser {quote_arg(player)}"
        if reason:
            cmd = f"{cmd} -r {quote_arg(reason)}"
        return await self.run(cmd)

    async def banuser(self, player: str) -> str:
        return await self.run(f"banuser {quote_arg(player)}")

    async def banid(self, steamid: str) -> str:
        return await self.run(f"banid {quote_arg(steamid)}")

    async def unbanuser(self, player: str) -> str:
        return await self.run(f"unbanuser {quote_arg(player)}")

    async def unbanid(self, steamid: str) -> str:
        return await self.run(f"unbanid {quote_arg(steamid)}")

    async def adduser(self, player: str, password: str) -> str:
        return await self.run(f"adduser {quote_arg(player)} {quote_arg(password)}")

    async def removeuserfromwhitelist(self, player: str) -> str:
        return await self.run(f"removeuserfromwhitelist {quote_arg(player)}")

    async def setaccesslevel(self, player: str, level: str) -> str:
        return await self.run(f"setaccesslevel {quote_arg(player)} {quote_arg(level)}")

    async def teleport(self, player: str, target: str) -> str:
        return await self.run(f"teleport {quote_arg(player)} {quote_arg(target)}")

    async def teleportto(self, player: str, x: int, y: int, z: int) -> str:
        return await self.run(f"teleportto {quote_arg(player)} {x},{y},{z}")

    async def additem(self, player: str, item: str, count: int) -> str:
        return await self.run(
            f"additem {quote_arg(player)} {quote_arg(item)} {count}"
        )

    async def addxp(self, player: str, perk: str, amount: int) -> str:
        return await self.run(
            f"addxp {quote_arg(player)} {quote_arg(f'{perk}={amount}')}"
        )

    async def addvehicle(self, script: str, player: str) -> str:
        return await self.run(f"addvehicle {quote_arg(script)} {quote_arg(player)}")

    async def createhorde(self, count: int, player: str) -> str:
        return await self.run(f"createhorde {count} {quote_arg(player)}")

    async def godmode(self, player: str) -> str:
        return await self.run(f"godmode {quote_arg(player)}")

    async def invisible(self, player: str) -> str:
        return await self.run(f"invisible {quote_arg(player)}")

    async def noclip(self, player: str) -> str:
        return await self.run(f"noclip {quote_arg(player)}")

    async def startrain(self) -> str:
        return await self.run("startrain")

    async def stoprain(self) -> str:
        return await self.run("stoprain")

    async def thunder(self) -> str:
        return await self.run("thunder")

    async def chopper(self) -> str:
        return await self.run("chopper")

    async def gunshot(self) -> str:
        return await self.run("gunshot")
