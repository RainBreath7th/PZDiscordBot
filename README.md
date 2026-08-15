# PZ Discord Bot

A Discord management bot for one Project Zomboid dedicated server. Semantic slash commands talk Source RCON.

Other languages: [中文](README.zh.md) · [日本語](README.jp.md)

## What it does

- `/players` — who is online
- `/restart queue|cancel|status|now` — empty-server queued restart or a forced restart
- Admin commands: `/announce` `/save` `/kick` `/ban` `/unban` `/whitelist` `/access` `/teleport` `/give` `/horde` `/player` `/weather`
- Bringing the game process back is **the existing PZ container's** `restart: unless-stopped`. The bot only sends `servermsg` → `save` → `quit`.

## Three Tiers

Configured in `config/permissions.yaml`, keyed by Discord `guild_id`. Roles are snowflake IDs.

| Tier | Who | Default commands |
|---|---|---|
| A | `admin_role_ids` | Full catalog; may cancel anyone's queue |
| B | `member_role_ids` (PZ member role) | `/players` + `/restart queue\|status`; cancel-own only |
| C | everyone else | `/players` only |

`command_min_tier` can lower a single command to B or C. Guilds missing from the file never receive slash commands. DMs are disabled.

## Deploy

This repo ships only the `pz-bot` image and `compose.bot.yaml`. The game server must already sit on a Docker network.

1. Copy `.env.example` to `.env` and set:
   - `DISCORD_TOKEN`
   - `RCON_HOST` / `RCON_PORT` / `RCON_PASSWORD` (no defaults — use your existing PZ service name and port)
   - `BOT_NETWORK` (the **external** network that already contains pz-server)
2. Edit `config/permissions.yaml`: replace the `000…` placeholders with a real `guild_id` and role IDs.
3. Adjust `config/i18n.yaml` (`discord_locales` and `game_locales` are independent) and `config/limits.yaml` as needed.
4. Start:

```bash
docker compose -f compose.bot.yaml up -d --build
```

Invite the bot with `bot` + `applications.commands`. After adding a guild, edit the yaml and `docker compose -f compose.bot.yaml restart pz-bot` (slash sync happens at startup only).

## Runtime

- Secrets stay in environment variables. `./config` is bind-mounted; yaml edits do not require a rebuild.
- Role maps / min tiers / channel allow-lists hot-reload. A bad file keeps the last-good config.
- The RestartQueue is in-memory. Timeout (default 7200s) cancels and never `quit`s. `RESTART_GRACE` defaults to 360s.
- Healthcheck: healthy if RCON answers **or** the bot is inside the planned RestartingWindow. `unhealthy` does not kill the container.
- Logs: `json-file`, `10m × 5`.

## Local development

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements-dev.txt
pytest
```

Code and comments are English. Domain terms live in [CONTEXT.md](CONTEXT.md).
