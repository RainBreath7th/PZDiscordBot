from __future__ import annotations

from bot.i18n import Translator, split_servermsg
from bot.players import PlayerCache
from bot.rcon_client import PlayerList, parse_players, quote_arg


def test_split_servermsg_does_not_truncate() -> None:
    text = "abcdefghij" * 5
    chunks = split_servermsg(text, 12)
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")
    assert all(len(chunk) <= 12 for chunk in chunks)
    assert len(chunks) > 1


def test_translator_game_messages_split(store) -> None:
    translator = Translator(store)
    messages = translator.game_messages("restart.queued")
    assert messages
    assert all(len(item) <= store.limits.servermsg_max_chars for item in messages)
    passthrough = translator.passthrough_game_messages("hello world from announce")
    assert len(passthrough) == len(store.i18n.game_locales) * 2 or len(passthrough) >= 2


def test_parse_players_common_formats() -> None:
    empty = parse_players("Players connected (0):\n")
    assert empty.count == 0
    assert empty.names == ()

    listed = parse_players("Players connected (2):\n- Alice\n- Bob\n")
    assert listed.count == 2
    assert listed.names == ("Alice", "Bob")

    messy = parse_players("Players connected (1)\n* \"Carol\"\n")
    assert messy.names == ("Carol",)


def test_player_cache_resolve_ambiguous() -> None:
    cache = PlayerCache()
    cache.update(PlayerList(count=2, names=("Alex", "Alexa")))
    assert cache.resolve("Alex") == "Alex"
    assert cache.resolve("Ale") == ("Alex", "Alexa")
    assert cache.resolve("nobody") == ()


def test_quote_arg_wraps_spaces() -> None:
    assert quote_arg("Bob") == "Bob"
    assert quote_arg("Bob Smith") == '"Bob Smith"'
    assert quote_arg('x"y') == 'x\\"y'
