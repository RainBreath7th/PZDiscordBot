from __future__ import annotations

from dataclasses import dataclass

from bot.rcon_client import PlayerList


@dataclass
class PlayerCache:
    listing: PlayerList = PlayerList(count=0, names=())

    def update(self, listing: PlayerList) -> None:
        self.listing = listing

    def names(self) -> tuple[str, ...]:
        return self.listing.names

    def resolve(self, typed: str) -> tuple[str, ...] | str:
        needle = typed.strip()
        if not needle:
            return ()
        exact = [name for name in self.listing.names if name.casefold() == needle.casefold()]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            return tuple(exact)
        partial = [
            name
            for name in self.listing.names
            if needle.casefold() in name.casefold()
        ]
        if len(partial) == 1:
            return partial[0]
        return tuple(partial)
