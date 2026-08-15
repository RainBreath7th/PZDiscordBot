# PZ Discord Bot

> Manage one Project Zomboid dedicated server from Discord. Every slash command is a plain verb (`/kick`, `/announce`) that talks Source RCON under the hood. There is no `/raw`, and the bot never touches the Docker socket.

Other languages: [中文](README.zh.md) · [日本語](README.jp.md) · [Entry](README.md)

---

## Contents

- [What is this](#what-is-this)
- [Quick start (5 minutes)](#quick-start-5-minutes)
- [1. Create and invite the Discord bot (step by step)](#1-create-and-invite-the-discord-bot-step-by-step)
- [2. Commands](#2-commands)
- [3. Permissions](#3-permissions)
- [4. Config files](#4-config-files)
- [5. Environment variables](#5-environment-variables)
- [6. Deployment](#6-deployment)
  - [6.1 Same host: PZ is in Docker](#61-same-host-pz-is-in-docker-composebotyaml)
  - [6.2 Remote: PZ is a Docker container on another machine](#62-remote-pz-is-a-docker-container-on-another-machine-composebotremoteyaml)
  - [6.3 PZ is not in Docker](#63-pz-is-not-in-docker-composebotnativeyaml)
  - [6.4 Run the bot without Docker](#64-run-the-bot-without-docker)
- [7. Local development & running](#7-local-development--running)
- [8. FAQ](#8-faq)
- [9. Project layout](#9-project-layout)

---

## What is this

- **What it manages:** One already-running Project Zomboid dedicated server. The bot talks to the game over RCON — the remote console protocol PZ exposes via `RCONPort` / `RCONPassword` in `servertest.ini`.
- **What it can do:** Check who is online (`/players`), queue an "restart when empty" job (`/restart queue`), broadcast to the game (`/announce`), and do day-to-day ops (`/kick`, `/ban`, …).
- **What it will not do:** Install mods, edit the map, or give you a web panel. It also does not `docker restart` the game container.
- **How restart really works:** The bot only sends `servermsg` (in-game broadcast) → `save` → `quit` (ask the PZ process to exit). Bringing the process back is the **game container's** `restart: unless-stopped`. The bot needs no Docker privileges.

### Replies & i18n

- **Discord side:** Each reply is one embed with one field per locale listed in `config/i18n.yaml` → `discord_locales` (default `zh`, `en`, `jp`). Query commands (`/players`, `/restart status`) are **public** so the whole channel can see them; mutating commands are **ephemeral** (only the caller sees the result) so ban reasons and SteamIDs do not leak to the channel.
- **In-game side:** Each announcement is sent once per locale in `game_locales`, as sequential `servermsg` lines. A single `servermsg` has a length limit (`servermsg_max_chars`, default 200), so a long line is split into multiple messages instead of being truncated.

---

## Quick start (5 minutes)

> If you already have a bot, skip to step 3. Otherwise start at step 1.

1. Follow [Chapter 1](#1-create-and-invite-the-discord-bot-step-by-step) to create a bot, copy `DISCORD_TOKEN`, and invite it to your server.
2. Turn on **Developer Mode** in Discord and copy the `guild_id` / role IDs (see [3.2](#32-how-to-copy-guild_id--role_id--user_id--channel_id)) into `config/permissions.yaml`.
3. Copy and fill the env file:

   ```bash
   cp .env.example .env
   # Edit .env: DISCORD_TOKEN / RCON_HOST / RCON_PORT / RCON_PASSWORD
   # BOT_NETWORK is only required when the PZ container and the bot share a host (see chapter 6)
   ```

4. Pick **one** compose file for your topology (do not start all three):

   ```bash
   # Same-host Docker (most common)
   docker compose -f compose.bot.yaml up -d --build
   docker compose -f compose.bot.yaml logs -f pz-bot

   # Remote Docker:   -f compose.bot.remote.yaml
   # PZ not in Docker: -f compose.bot.native.yaml
   ```

5. In Discord, try `/players`. If you see a headcount, RCON is connected.

---

## 1. Create and invite the Discord bot (step by step)

> Official docs: [Discord Developer Portal — Applications](https://discord.com/developers/applications) · [discord.py docs](https://discordpy.readthedocs.io/en/stable/)

### 1.1 Create an Application

1. Open <https://discord.com/developers/applications> → **New Application** → give it a name (e.g. `PZ-Bot`) → Create.
2. On **General Information**, note the **Application ID** (also called `client_id` — you need it for the invite URL).

### 1.2 Create the bot and copy the token

1. Go to **Bot** → **Add Bot** (or open the existing one).
2. Under **Token**, click **Reset Token** (or **Copy** on first creation) and copy the value. **This is `DISCORD_TOKEN` in `.env`. Never paste it in a public channel or commit it to git.**
3. **Privileged Gateway Intents:** This project does **not** need `Presence Intent`, `Server Members Intent`, or `Message Content`. Leave them off (the code uses `Intents.default()` only).
4. Paste the token into `.env`:

   ```
   DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OTA.GhIjKl.MnOpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUv
   ```

### 1.3 Generate an invite URL

1. Go to **OAuth2 → URL Generator**.
2. Under **Scopes**, check:
   - `bot`
   - `applications.commands` (without this, slash commands never appear)
3. Under **Bot Permissions**, check at minimum:
   - `Send Messages`
   - `Embed Links`
   - `Read Message History` (optional, handy)
   - You do **not** need `Administrator`.
4. Copy the **Generated URL** at the bottom. It looks like:

   ```
   https://discord.com/api/oauth2/authorize?client_id=123456789012345678&permissions=274877908032&scope=bot%20applications.commands
   ```

   Replace `123456789012345678` with your **Application ID**. The `permissions` number is computed from the checkboxes — just use what the page generates.

### 1.4 Invite the bot to your server

1. Open the URL in a browser logged in as a server admin.
2. Pick the target server → **Authorize** → complete the captcha.
3. Back in Discord you will see the bot in the member list (grey/offline until the container starts, green after).

### 1.5 Keep the token safe

- A token is a password. If it leaks, go to **Developer Portal → Bot → Reset Token** immediately, update `.env`, and restart: `docker compose -f compose.bot.yaml restart pz-bot`.
- All secrets stay in environment variables. They never go into `config/*.yaml` and are not baked into the image.

---

## 2. Commands

> Slash commands are synced only to the servers listed in `config/permissions.yaml` (`guilds` keys). Servers not listed see no commands at all. DMs are disabled.
>
> Every RCON-backed command defers within 3 seconds (shows "Bot is thinking…") before contacting the game, so Discord does not time out.
>
> **Autocomplete:** Every `player` parameter autocompletes from the live online list. You can pick a suggestion or type the full character name by hand. Ambiguous names are rejected with a list — the bot never guesses.

### 2.1 Query & restart (most used)

| Command | Parameters | What it does | Default min tier | Visibility | Needs confirmation |
|---|---|---|---|---|---|
| `/players` | none | Show who is online and how many. Also refreshes the cache used for autocomplete. | C (everyone) | Public | No |
| `/restart queue` | none | Queue a restart that runs **when the server becomes empty**. While people are online it polls `players` every `POLL_INTERVAL` (default 30s). When the count hits 0 it **waits `EMPTY_CONFIRM_SECONDS` (default 10s) and checks again**; only if both checks are 0 does it broadcast → `save` → `quit`. On timeout (`RESTART_TIMEOUT` default 7200s) it only cancels — it never forces a quit. | B | Ephemeral | No |
| `/restart cancel` | none | Cancel the queued restart. Tier B can only cancel their own; Tier A can cancel anyone's. | B (plus owner check) | Ephemeral | No |
| `/restart status` | none | Show queue state or how much grace is left in the restarting window. Public so anyone in the channel can check. | B | Public | No |
| `/restart now` | none | Do not wait — broadcast → `save` → `quit` right now. If a queue exists it is cancelled first. | A | Ephemeral | **Yes** (Confirm/Cancel, 30s, only the caller can press) |

**In-game chatter during restart:** `queue` broadcasts once (per `game_locales`) when the queue is created, and once more right before `save`/`quit`; `now` only broadcasts the second one. Timeouts and user cancels do not broadcast, and the bot does not spam periodic reminders.

**Restarting window:** After `save`/`quit`, the bot enters a `RestartingWindow` (`RESTART_GRACE` default 360s ≈ 6 min on this host). During the window every command except `/restart status` is rejected with "restarting, N seconds left", so the bot does not hammer a dead RCON port. After the window, a still-dead RCON is treated as a normal failure.

### 2.2 Basic ops

| Command | Parameters | What it does | Default min tier | Visibility | Needs confirmation |
|---|---|---|---|---|---|
| `/announce` | `message`: string (required) | Broadcast exactly what you typed, once per `game_locales`, as `servermsg`. No translation — what you type is what players see. Long lines are split at `servermsg_max_chars` (default 200). | A | Ephemeral | No |
| `/save` | none | Save the world without restarting. | A | Ephemeral | No |

### 2.3 Session (kick / ban / whitelist / access)

| Command | Parameters | What it does | Default min tier | Visibility | Needs confirmation |
|---|---|---|---|---|---|
| `/kick` | `player`: character name (required, autocomplete)<br>`reason`: string (optional) | Kick an online player. Wraps `kickuser`. | A | Ephemeral | **Yes** |
| `/ban user` | `player`: character name (required) | Ban by character name. Wraps `banuser`. | A | Ephemeral | **Yes** |
| `/ban steamid` | `steamid`: SteamID string (required) | Ban by SteamID. Wraps `banid`. Works while the player is offline. | A | Ephemeral | **Yes** |
| `/unban user` | `player`: character name (required) | Unban by character name. Wraps `unbanuser`. | A | Ephemeral | **Yes** |
| `/unban steamid` | `steamid`: SteamID string (required) | Unban by SteamID. Wraps `unbanid`. | A | Ephemeral | **Yes** |
| `/whitelist add` | `player`: account name (required)<br>`password`: password (required) | Add an account to the whitelist. Wraps `adduser`. | A | Ephemeral | No |
| `/whitelist remove` | `player`: account name (required) | Remove an account from the whitelist. Wraps `removeuserfromwhitelist`. | A | Ephemeral | **Yes** |
| `/access set` | `player`: character name (required, autocomplete)<br>`level`: choice (required: `none` / `observer` / `gm` / `overseer` / `moderator` / `admin`) | Change in-game access level. Wraps `setaccesslevel`. **Break-glass:** If the target is already `admin`, only users in `break_glass_user_ids` may change them; when the list is empty, no existing admin can be changed (you can still promote non-admins). | A (+ break-glass) | Ephemeral | **Yes** |

### 2.4 Teleport, give, horde, player flags

| Command | Parameters | What it does | Default min tier | Visibility | Needs confirmation |
|---|---|---|---|---|---|
| `/teleport to-player` | `player`: who to move (required)<br>`target`: destination player (required) | Teleport `player` to `target`. Wraps `teleport`. | A | Ephemeral | No |
| `/teleport to-coords` | `player`: character name (required)<br>`x` / `y` / `z`: integers (required) | Teleport to coordinates. Wraps `teleportto`. | A | Ephemeral | No |
| `/give item` | `player`: character name (required)<br>`item`: script name e.g. `Base.Axe` (required)<br>`count`: integer (optional, default 1, clamped by `limits.yaml`) | Give items. Wraps `additem`. A bad script name returns the raw RCON reply. | A | Ephemeral | No |
| `/give xp` | `player`: character name (required)<br>`perk`: perk name e.g. `Woodwork` (required)<br>`amount`: integer (required, clamped) | Give perk XP. Wraps `addxp`. | A | Ephemeral | No |
| `/give vehicle` | `player`: character name (required)<br>`script`: vehicle script (required) | Spawn a vehicle near the player. Wraps `addvehicle`. | A | Ephemeral | No |
| `/horde` | `player`: character name (required)<br>`count`: integer (required, clamped) | Spawn a horde near the player. Wraps `createhorde`. | A | Ephemeral | No |
| `/player god` | `player`: character name (required) | Toggle godmode. Wraps `godmode`. | A | Ephemeral | No |
| `/player invisible` | `player`: character name (required) | Toggle invisibility. Wraps `invisible`. | A | Ephemeral | No |
| `/player noclip` | `player`: character name (required) | Toggle noclip. Wraps `noclip`. | A | Ephemeral | No |

> Count limits live in `config/limits.yaml` and hot-reload: `item 1–50`, `xp 1–100000`, `horde 1–50`, `vehicle` is always 1. Out-of-range requests are rejected, not clamped and executed.

### 2.5 Weather & events

| Command | Parameters | What it does | Default min tier | Visibility | Needs confirmation |
|---|---|---|---|---|---|
| `/weather start-rain` | none | Start rain. Wraps `startrain`. | A | Ephemeral | No |
| `/weather stop-rain` | none | Stop rain. Wraps `stoprain`. | A | Ephemeral | No |
| `/weather thunder` | none | Trigger thunder. Wraps `thunder`. | A | Ephemeral | No |
| `/weather chopper` | none | Trigger a helicopter event. Wraps `chopper`. | A | Ephemeral | No |
| `/weather gunshot` | none | Trigger a gunshot event. Wraps `gunshot`. | A | Ephemeral | No |

---

## 3. Permissions

### 3.1 What is `guild_id` / `role_id` / `user_id` / `channel_id`?

- **Guild** is Discord's word for **a server**. So `guild_id` in the config is "your Discord server's ID".
- **Role / User / Channel IDs** are the same idea — Discord **snowflake IDs**, long numeric strings like `"123456789012345678"`. Always use the ID, not the display name.
- Why IDs? Role names can be renamed; matching by name would silently break permissions. IDs never change.

### 3.2 How to copy `guild_id` / `role_id` / `user_id` / `channel_id`

1. In Discord: **Settings → Advanced → enable Developer Mode**.
   - Desktop: gear at the bottom-left → Advanced.
   - Mobile: Settings → Advanced.
2. Back in the server:
   - **Server ID (`guild_id`):** right-click the server icon → **Copy ID**.
   - **Role ID (`role_id`):** Server Settings → Roles → right-click a role → **Copy ID**.
   - **User ID (`user_id`):** right-click a member → **Copy ID**.
   - **Channel ID (`channel_id`):** right-click a channel → **Copy ID**.
3. Paste the numbers **inside quotes** in `config/permissions.yaml`. Without quotes YAML may treat large numbers as floats.

### 3.3 Three tiers

| Tier | Field | Typical who | Default access |
|---|---|---|---|
| **A** | `admin_role_ids` | Server owners / moderators | Full catalog; may cancel anyone's `/restart queue`; may run `/restart now` |
| **B** | `member_role_ids` | Regular PZ players / `@pz` role | `/players` + `/restart queue` + `/restart status`; cancel-own only |
| **C** | everyone else | Everyone else / `@everyone` | `/players` only |

- If someone holds both A and B roles, the **highest tier (A) wins**.
- Defaults live in `bot/constants.py` (`DEFAULT_MIN_TIER`); `command_min_tier` in the YAML can lower a single command to B or C without code changes.

### 3.4 `config/permissions.yaml` example (copy and edit)

```yaml
# Only servers listed here receive slash commands. Restart the bot after adding a server.
guilds:
  # Your Discord server ID (right-click the server icon → Copy ID)
  "123456789012345678":
    # Tier-A: owners / moderators. Keep this to 1–2 trusted roles.
    admin_role_ids:
      - "111111111111111111"   # @Admin
      - "222222222222222222"   # @Moderator (if you want co-owners to manage)

    # Tier-B: regular PZ players. Anyone with this role may queue a restart.
    member_role_ids:
      - "333333333333333333"   # @pz / @Survivor

    # (Optional) Only allow commands in these channels. Empty = any channel in this server.
    command_channel_ids: []
    # Example: restrict to #pz-ops
    # command_channel_ids:
    #   - "444444444444444444"

    # (Optional) Break-glass: Discord user IDs allowed to change someone who is already in-game admin.
    # Empty = changing an existing admin is forbidden (you can still promote non-admins).
    break_glass_user_ids:
      - "555555555555555555"   # owner's Discord user ID

    # (Optional) Per-command minimum tier overrides. Keys must be in the allow-list below.
    command_min_tier:
      # Let Tier-B also announce:
      # announce: B
      # Let everyone see status (default is B):
      # restart_status: C

    # Allowed override keys (wrong keys fail at startup):
    # players, restart_queue, restart_cancel, restart_status, restart_now,
    # announce, save, kick, ban, unban, whitelist, access,
    # teleport, give, horde, player, weather
```

**Field notes:**

- `admin_role_ids` / `member_role_ids`: arrays of role IDs as strings. A typo here is the most common "permission denied" cause.
- `command_channel_ids`: array of channel IDs. Empty = no restriction. When set, commands outside those channels reply "use an allowed channel".
- `break_glass_user_ids`: array of user IDs. See `/access set` in [2.3](#23-session-kick--ban--whitelist--access).
- `command_min_tier`: map from command key to `A` / `B` / `C` (case-insensitive).

### 3.5 Hot reload & adding a server

- **Changing roles / `command_min_tier` / `command_channel_ids` / `break_glass_user_ids`:** Edit `config/permissions.yaml`. The next command picks it up (the bot checks file `mtime`; a bad file keeps the last-good config and logs an error).
- **Adding or removing a server (changing `guilds` keys):** Slash registration only happens **at startup** for each key in `guilds`. After adding a server:

  ```bash
  docker compose -f compose.bot.yaml restart pz-bot
  # or without Docker: systemctl restart pz-discord-bot
  ```

- Servers not in `guilds` see no commands. DMs are disabled.

---

## 4. Config files

| File | Purpose | Hot reload | What happens if it is broken |
|---|---|---|---|
| `config/permissions.yaml` | Permissions & channel allow-list (see above) | Yes (roles/channels/overrides live; new guild needs restart) | Startup fails, or last-good is kept at runtime |
| `config/i18n.yaml` | Which locales to show | Yes | Startup fails |
| `config/limits.yaml` | Numeric caps & misc | Yes | Startup fails |
| `config/locales/zh.yaml` `en.yaml` `jp.yaml` | Message bundles | Yes | Startup fails |

### 4.1 `config/i18n.yaml`

```yaml
# One field per locale in each Discord embed
discord_locales:
  - zh
  - en
  - jp
# One sequential servermsg per locale in-game
game_locales:
  - zh
  - en
  - jp
```

- Slash names and option names are always English (Discord limitation).
- The bot does not switch by the caller's Discord client language; it follows this file.
- Supported locales: `zh`, `en`, `jp`, in the order listed.

### 4.2 `config/limits.yaml`

```yaml
item_count:
  min: 1
  max: 50
xp:
  min: 1
  max: 100000
vehicle: 1          # always 1
horde:
  min: 1
  max: 50
servermsg_max_chars: 200   # max chars per servermsg (long lines are split)
confirm_timeout_seconds: 30
```

---

## 5. Environment variables

> Copy `.env.example` to `.env` and fill it. Never commit `.env`.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DISCORD_TOKEN` | **yes** | — | Bot token (see 1.2) |
| `RCON_HOST` | **yes** | — | RCON host. What you write depends on the topology — see [the table in chapter 6](#6-deployment). **No default — you must write it.** |
| `RCON_PORT` | **yes** | — | RCON port (PZ default 27015, but use your `servertest.ini` `RCONPort`) |
| `RCON_PASSWORD` | **yes** | — | RCON password (`RCONPassword`) |
| `BOT_NETWORK` | **only** [compose.bot.yaml](compose.bot.yaml) | — | **External** Docker network that already contains the PZ container. The Python process does not read this; leave it blank for remote / native topologies |
| `POLL_INTERVAL` | no | `30` | Seconds between `players` polls while queued |
| `RESTART_TIMEOUT` | no | `7200` | Queue timeout in seconds; on expiry it only cancels |
| `RESTART_GRACE` | no | `360` | Grace after `save`+`quit` (≈ 6 min cold start on this host) |
| `RCON_FAIL_THRESHOLD` | no | `3` | Consecutive RCON failures while queued before cancelling |
| `EMPTY_CONFIRM_SECONDS` | no | `10` | Gap between the two empty checks |
| `RCON_TIMEOUT` | no | `10` | Per-RCON-call timeout in seconds |
| `CONFIG_DIR` | no | `config` (`/app/config` in container) | Config directory |
| `HEALTH_STATE_PATH` | no | `/tmp/pz-bot-health.json` | Health state file (tells "planned restart" from "really down") |
| `LOG_LEVEL` | no | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## 6. Deployment

This repo ships **only the bot**. The game server is assumed to already be running somewhere — a Docker container or a native process. Three compose files cover three topologies. **Start only one of them.** The service is always `pz-bot`; the image is always `pz-discord-bot:latest`.

| Your setup | File | What to put in `RCON_HOST` | Need `BOT_NETWORK`? |
|---|---|---|---|
| PZ is a Docker container on the **same** machine as the bot | [compose.bot.yaml](compose.bot.yaml) | PZ compose **service name** (e.g. `pz-server`) | **yes** |
| PZ is a Docker container on a **different** machine | [compose.bot.remote.yaml](compose.bot.remote.yaml) | That machine's **LAN IP** (e.g. `10.0.0.5`) | no |
| PZ is **not** in Docker (bare process / systemd) | [compose.bot.native.yaml](compose.bot.native.yaml) | Same host: `host.docker.internal`. Remote: LAN IP | no |

Shared by all three files (already written — you do not edit these):

- Only the `pz-bot` service; it does not start another game server.
- `restart: unless-stopped`.
- `volumes: ./config:/app/config` — YAML edits need no rebuild.
- `logging: json-file, max-size 10m, max-file 5`.
- `healthcheck: python -m bot.health` — healthy if RCON answers **or** the bot is inside the planned restarting window; `unhealthy` does not kill the container; `start_period` aligns with `RESTART_GRACE` (360s).
- **No `docker.sock` mount**, and the bot **does not publish the RCON port**.

Restart still works the same way: the bot only sends `servermsg` → `save` → `quit`. Bringing the process back is the game server's job (the container's `restart: unless-stopped`, or whatever systemd / watchdog you attached to a native process).

Day-to-day commands — swap the file name for the one you picked:

```bash
docker compose -f compose.bot.yaml restart pz-bot   # required after changing the guild list
docker compose -f compose.bot.yaml down
docker compose -f compose.bot.yaml logs -f pz-bot
docker inspect --format='{{json .State.Health}}' pz-discord-bot-pz-bot-1 | python -m json.tool
```

---

### 6.1 Same host: PZ is in Docker (`compose.bot.yaml`)

> Most common, and the safest. The bot joins the existing PZ network. RCON stays on Docker's internal DNS. **Do not publish the RCON port to the host or the public internet.**

**Step 1 — Find the PZ network name**

```bash
docker network ls
# Look for pz_default, pz-server_default, or a custom pz-net
docker inspect <pz-server-container> --format '{{json .NetworkSettings.Networks}}' | python -m json.tool
```

Note the network name → put it in `.env` as `BOT_NETWORK`.

**Step 2 — Prepare `.env` and `config/permissions.yaml`**

```bash
cp .env.example .env
# Edit .env:
#   DISCORD_TOKEN=...
#   RCON_HOST=pz-server          # PZ compose service name, not localhost
#   RCON_PORT=27015              # match servertest.ini RCONPort
#   RCON_PASSWORD=...
#   BOT_NETWORK=pz_default       # the name from step 1
# Edit config/permissions.yaml: replace 000… with real guild_id / role IDs
```

`RCON_HOST` is the **service name** (Docker internal DNS can resolve it). **Do not write `localhost`** — that is the bot container's own loopback, which cannot see the neighbour container.

**Step 3 — Start**

```bash
docker compose -f compose.bot.yaml up -d --build
docker compose -f compose.bot.yaml logs -f pz-bot
# Look for "synced slash commands" and "bot ready"
```

This file requires `BOT_NETWORK`: compose refuses to start if it is missing. The network must already exist (`external: true`); compose will **not** create it for you.

---

### 6.2 Remote: PZ is a Docker container on another machine (`compose.bot.remote.yaml`)

> The bot cannot join another host's Docker network, so it reaches RCON over the LAN. `BOT_NETWORK` is unused; the Python process does not read it.

**On the PZ host** (not this repo) you must publish RCON **only to the LAN IP**, never to `0.0.0.0`:

```yaml
# Fragment of the existing pz-server compose — not in this repo
ports:
  - "10.0.0.5:27015:27015"    # host-LAN:host-port:container-port
# Do not write "27015:27015" (that binds 0.0.0.0 — the public internet).
```

Firewall: allow the bot host only, for example:

```bash
# On the PZ host, allow only the bot host 10.0.0.8 to reach 27015
sudo ufw allow from 10.0.0.8 to any port 27015 proto tcp
```

**On the machine that runs the bot:**

```bash
cp .env.example .env
# Edit .env:
#   DISCORD_TOKEN=...
#   RCON_HOST=10.0.0.5          # PZ host LAN IP, not a service name, avoid a public IP
#   RCON_PORT=27015             # the host port published above
#   RCON_PASSWORD=...
#   BOT_NETWORK can stay empty

docker compose -f compose.bot.remote.yaml up -d --build
docker compose -f compose.bot.remote.yaml logs -f pz-bot
```

This file has **no** `networks:` block and **no** port mapping. Restart is still the PZ container's `restart: unless-stopped`; this bot will not, and cannot, `docker restart` a container on another machine.

Sanity-check from the bot host before starting:

```bash
nc -vz 10.0.0.5 27015
# or: python -c "import socket; s=socket.create_connection(('10.0.0.5',27015),5); print('ok'); s.close()"
```

---

### 6.3 PZ is not in Docker (`compose.bot.native.yaml`)

> PZ is a native process (official dedicated, steamcmd, a systemd unit, …). There is no Docker network to join. The bot container has to reach RCON through the host.

**What to put in `RCON_HOST`:**

| Where PZ lives | `RCON_HOST` |
|---|---|
| **Same** machine as the bot | `host.docker.internal` (the compose file already adds `extra_hosts: host.docker.internal:host-gateway`) |
| A **different** machine | That machine's LAN IP (same network path as 6.2) |

**The catch:** a container cannot see the host's `127.0.0.1`. If PZ binds RCON to `127.0.0.1` only, `host.docker.internal` will also fail. Pick one:

1. Bind PZ RCON to `0.0.0.0` or the LAN NIC, firewall it to the Docker bridge / the bot host, then use `host.docker.internal`.
2. **Linux only:** uncomment `network_mode: host` in [compose.bot.native.yaml](compose.bot.native.yaml), set `RCON_HOST=127.0.0.1`, and drop `extra_hosts`. Docker Desktop on Windows / macOS does not offer real host networking.

**On the machine that runs the bot:**

```bash
cp .env.example .env
# Edit .env:
#   DISCORD_TOKEN=...
#   RCON_HOST=host.docker.internal   # same host; use a LAN IP if PZ is elsewhere
#   RCON_PORT=27015
#   RCON_PASSWORD=...
#   BOT_NETWORK can stay empty

docker compose -f compose.bot.native.yaml up -d --build
docker compose -f compose.bot.native.yaml logs -f pz-bot
```

Restart is on you: the bot still only sends `servermsg` → `save` → `quit`. A native process has no `restart: unless-stopped`, so you need systemd / a watchdog to bring PZ back, or `/restart` will leave the game down.

---

### 6.4 Run the bot without Docker

> The bot itself is a host process. Works with all three PZ topologies; only `RCON_HOST` changes.

**Step 1 — Python**

```bash
# Requires Python 3.12+
python3 --version

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Step 2 — Config and env**

```bash
cp .env.example .env
# BOT_NETWORK is not needed (compose.bot.yaml only)
# RCON_HOST:
#   PZ native / Docker-published on this host → 127.0.0.1
#   PZ on another machine                     → LAN IP
```

You can also skip `.env` and `export` directly:

```bash
export DISCORD_TOKEN=...
export RCON_HOST=127.0.0.1
export RCON_PORT=27015
export RCON_PASSWORD=...
export CONFIG_DIR=$(pwd)/config
```

**Step 3 — Run in the foreground**

```bash
# If you used .env (requires manual export; python-dotenv is not bundled)
export $(cat .env | xargs)   # only if .env has no spaces/quotes
python -m bot

# Or one-shot:
DISCORD_TOKEN=... RCON_HOST=127.0.0.1 RCON_PORT=27015 RCON_PASSWORD=... python -m bot
```

Look for `bot ready`. `Ctrl+C` to stop.

**Step 4 — Keep it running with systemd (Linux)**

Create `/etc/systemd/system/pz-discord-bot.service`:

```ini
[Unit]
Description=PZ Discord Bot
After=network.target

[Service]
User=pzbot
WorkingDirectory=/opt/pz-discord-bot
EnvironmentFile=/opt/pz-discord-bot/.env
ExecStart=/opt/pz-discord-bot/.venv/bin/python -m bot
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pz-discord-bot
sudo systemctl status pz-discord-bot
sudo journalctl -u pz-discord-bot -f
```

**Health check without Docker:**

```bash
python -m bot.health; echo $?
# 0 = healthy, 1 = unhealthy
```

---

## 7. Local development & running

### 7.1 Setup

```bash
python3 --version   # 3.12+
python -m venv .venv
source .venv/bin/activate   # Windows Git Bash: source .venv/Scripts/activate
                            # Windows CMD:      .venv\Scripts\activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` adds `pytest` / `pytest-asyncio`.

### 7.2 Configure and start (dev)

```bash
cp .env.example .env
# Fill DISCORD_TOKEN / RCON_HOST / RCON_PORT / RCON_PASSWORD
# For local dev use the non-Docker path (see 6.4) — no need for BOT_NETWORK
# Put only a test server's guild_id in permissions.yaml at first

python -m bot
# Or one-shot:
# DISCORD_TOKEN=... RCON_HOST=... RCON_PORT=... RCON_PASSWORD=... python -m bot
```

- On first start you will see `synced slash commands` (one sync per guild in `permissions.yaml`).
- Slash commands are cached by Discord for up to an hour; when testing, try re-inviting the bot or waiting a bit.

### 7.3 Tests

```bash
pytest -q
# verbose
pytest -v
```

Covers: tier matrix, hot reload, i18n splitting, `players` parsing, the restart state machine (enqueue / reject / timeout / double-zero / preempt / consecutive failures), and health state.

### 7.4 Logs

- Local: `stdout` JSON lines (`ts` / `level` / `msg` / `operator` / `rcon_cmd` / `queue_state`).
- Docker: `docker compose -f compose.bot.yaml logs -f pz-bot` (swap the file for `compose.bot.remote.yaml` / `compose.bot.native.yaml` on those topologies).
- systemd: `journalctl -u pz-discord-bot -f`.

---

## 8. FAQ

**Slash commands do not appear.**

- Invite URL included `applications.commands`.
- `config/permissions.yaml` contains your `guild_id` (right-click server icon → Copy ID) as a quoted string.
- The bot was restarted after editing the guild list; logs show `synced slash commands`.
- Discord caches for up to an hour — try re-inviting or waiting.

**"Insufficient permissions."**

- Your account actually has a role listed in `admin_role_ids` or `member_role_ids` (right-click the role → Copy ID and compare).
- `command_min_tier` did not raise the command's minimum tier.
- `command_channel_ids` did not restrict the channel you are in.

**"Server is restarting, N seconds left."**

- This is the normal `RestartingWindow` (default 360s). Right after `save`/`quit`, everything except `/restart status` is blocked so the bot does not hammer a dead RCON port. Wait for the window to end.

**RCON failures.**

- `RCON_HOST` / `RCON_PORT` / `RCON_PASSWORD` match `servertest.ini`.
- Same-host Docker (`compose.bot.yaml`): `RCON_HOST` is the service name (e.g. `pz-server`), not `localhost`; `BOT_NETWORK` is the same network as the PZ container.
- Remote Docker (`compose.bot.remote.yaml`): `RCON_HOST` is the PZ host LAN IP; RCON is published only to the LAN and the firewall allows only the bot host.
- Native PZ (`compose.bot.native.yaml`): same host → `host.docker.internal`, never `127.0.0.1` (that is the bot container itself); remote → LAN IP.
- Bot not in Docker: the firewall allows the RCON port, and RCON is bound to an internal address or `127.0.0.1` (do not expose it publicly).
- Check log fields `rcon_cmd` and `detail`.

**Edits to `permissions.yaml` do not take effect.**

- Role / channel / tier overrides: next command picks them up (hot reload).
- Adding or removing a server (changing `guilds` keys): restart the bot.

**The bot fails to start after editing `permissions.yaml`.**

- Bad YAML or a bad `command_min_tier` key fails startup. A bad edit at runtime keeps the last-good config and logs an `error` — it will not silently become "everyone is C" or "everyone is A".

---

## 9. Project layout

```
.
├── bot/                 # Python package (discord.py + RCON + queue + permissions + i18n)
│   ├── app.py           # Build the bot, register cogs, sync slash per guild
│   ├── settings.py      # Env vars
│   ├── config.py        # YAML loading & mtime hot reload
│   ├── permissions.py   # Three tiers + channel / break-glass checks
│   ├── rcon_client.py   # async Source RCON wrapper & players parsing
│   ├── restart_queue.py # Global RestartQueue state machine
│   ├── discord_util.py  # Gates, embeds, i18n, confirm buttons
│   └── cogs/            # Slash command groups
├── config/
│   ├── permissions.yaml
│   ├── i18n.yaml
│   ├── limits.yaml
│   └── locales/{zh,en,jp}.yaml
├── compose.bot.yaml         # Same host: PZ container + bot
├── compose.bot.remote.yaml  # Remote: PZ container on another machine
├── compose.bot.native.yaml  # PZ is not in Docker
├── Dockerfile
├── requirements.txt / requirements-dev.txt
└── tests/               # pytest
```

Glossary in [CONTEXT.md](CONTEXT.md). Code and comments are English.
