from __future__ import annotations

from bot.config import ConfigStore


def split_servermsg(text: str, max_chars: int) -> list[str]:
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    text = text.strip("\n")
    if not text:
        return [""]
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        window = remaining[:max_chars]
        cut = window.rfind(" ")
        if cut < max_chars // 4:
            cut = max_chars
        piece = remaining[:cut].rstrip()
        if not piece:
            piece = remaining[:max_chars]
            cut = max_chars
        chunks.append(piece)
        remaining = remaining[cut:].lstrip()
    return chunks


class Translator:
    def __init__(self, store: ConfigStore) -> None:
        self.store = store

    def render(self, locale: str, key: str, **kwargs: object) -> str:
        template = self.store.lookup(locale, key)
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template

    def discord_lines(self, key: str, **kwargs: object) -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = []
        for locale in self.store.i18n.discord_locales:
            lines.append((locale, self.render(locale, key, **kwargs)))
        return lines

    def game_messages(self, key: str, **kwargs: object) -> list[str]:
        max_chars = self.store.limits.servermsg_max_chars
        out: list[str] = []
        for locale in self.store.i18n.game_locales:
            text = self.render(locale, key, **kwargs)
            out.extend(split_servermsg(text, max_chars))
        return out

    def passthrough_game_messages(self, message: str) -> list[str]:
        max_chars = self.store.limits.servermsg_max_chars
        out: list[str] = []
        for _locale in self.store.i18n.game_locales:
            out.extend(split_servermsg(message, max_chars))
        return out
