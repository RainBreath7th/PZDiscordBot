# PZ Discord Bot

> Manage one Project Zomboid dedicated server from Discord. Slash commands only, no `/raw`, no Docker socket.

- **中文**：[README.zh.md](README.zh.md) — 完整说明、手把手申请与部署、每条命令的参数表
- **English**：[README.en.md](README.en.md) — Full guide, step-by-step bot setup, per-command tables
- **日本語**：[README.jp.md](README.jp.md) — 完全ガイド、Bot 作成手順、コマンド一覧

## What this repo ships

Only the bot. Pick **one** compose file for your topology — they all build `rainbreath/pz-discord-bot:latest` and start a single `pz-bot` service:

| Topology | File | `RCON_HOST` | `BOT_NETWORK` |
|---|---|---|---|
| PZ is a container on **this** host | [compose.bot.yaml](compose.bot.yaml) | PZ compose service name | required |
| PZ is a container on **another** host | [compose.bot.remote.yaml](compose.bot.remote.yaml) | PZ host LAN IP | unused |
| PZ is **not** in Docker | [compose.bot.native.yaml](compose.bot.native.yaml) | `host.docker.internal` or a LAN IP | unused |

Or run the process directly: `python -m bot` (see the language-specific READMEs).

The game server itself is not in this repo.

## Quick links

- Commands & permissions → see the language READMEs above. Every command is listed in a table with parameters, purpose, default tier, visibility, and whether it needs confirmation.
- `guild_id` / role IDs → how to copy them and a copy-pasteable [`config/permissions.yaml`](config/permissions.yaml) example are in each README.
- Discord bot setup → [README.zh.md §1](README.zh.md#1-discord-机器人申请与邀请手把手) / [README.en.md §1](README.en.md#1-create-and-invite-the-discord-bot-step-by-step) / [README.jp.md §1](README.jp.md#1-discord-bot-の作成と招待手順どおり) (Developer Portal → Bot → Token → OAuth2 invite URL).
- Deploy topologies → [README.zh.md §6](README.zh.md#6-部署) / [README.en.md §6](README.en.md#6-deployment) / [README.jp.md §6](README.jp.md#6-デプロイ) (same-host Docker / remote Docker / native PZ).

## Tech stack

| Layer | Choice | Version / detail | Why |
|---|---|---|---|
| Runtime | Python | **3.12** (`python:3.12-slim` in [Dockerfile](Dockerfile)) | Lean image, no build stage needed; matches `PZ_Discord_Bot_Tech_Selection.md` |
| Discord | [discord.py](https://github.com/Rapptz/discord.py) | **≥ 2.7** (`discord.ext.tasks` for the empty-server poll, `app_commands` + `GroupCog` for slash) | Background queue is a first-class citizen; richer than hikari/pycord for this ops bot |
| RCON | [rcon](https://github.com/conqp/rcon) (async Source RCON) | **≥ 2.4.9** (`rcon.source.rcon` async + thin wrapper in `bot/rcon_client.py`) | Async-native so slash handlers can `defer` then `await` without blocking the gateway; `zomboid-rcon` is only used as a command-name reference |
| Config | [PyYAML](https://pyyaml.org/) | **≥ 6.0.1** | `config/permissions.yaml` / `i18n.yaml` / `limits.yaml` + `mtime` hot-reload with last-good fallback |
| i18n | Custom `Translator` + `servermsg` splitter | `discord_locales` / `game_locales` independent; `servermsg_max_chars` (default 200) | One Discord reply shows N locales as Embed fields; in-game messages are sent sequentially per locale |
| Queue | In-memory global `RestartQueue` | `POLL_INTERVAL` 30s, `EMPTY_CONFIRM_SECONDS` 10s (double-zero), `RESTART_TIMEOUT` 7200s, `RESTART_GRACE` 360s | Single lock for one PZ server; `save` failure never `quit`s; `RestartingWindow` gates all but `/restart status` |
| Container | Docker + Compose | three bot-only files (`pz-bot` service, `image: rainbreath/pz-discord-bot:latest`, `restart: unless-stopped`, `json-file` 10m×5, `HEALTHCHECK python -m bot.health`): [compose.bot.yaml](compose.bot.yaml) joins the existing PZ network; [compose.bot.remote.yaml](compose.bot.remote.yaml) / [compose.bot.native.yaml](compose.bot.native.yaml) reach RCON over the host/LAN | Game process does the real restart; bot never mounts `docker.sock` and never publishes RCON |
| Tests | [pytest](https://pytest.org/) + pytest-asyncio | `pytest ≥ 8`, `asyncio_mode = auto` | Tier matrix, hot-reload, `players` parsing, queue state machine |

Decision rationale lives in [PZ_Discord_Bot_Tech_Selection.md](PZ_Discord_Bot_Tech_Selection.md).
