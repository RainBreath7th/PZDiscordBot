# PZ Discord Bot

> 用 Discord 斜杠命令管一台 Project Zomboid 专用服务器。所有命令都是“说人话的动词”（`/kick`、`/announce`），背后走 Source RCON。没有 `/raw`，也不会去动 Docker。

其他语言：[English](README.en.md) · [日本語](README.jp.md) · [入口](README.md)

---

## 目录

- [这是什么](#这是什么)
- [快速开始（5 分钟跑起来）](#快速开始5-分钟跑起来)
- [1. Discord 机器人申请与邀请（手把手）](#1-discord-机器人申请与邀请手把手)
- [2. 支持的命令](#2-支持的命令)
- [3. 权限管理](#3-权限管理)
- [4. 配置文件](#4-配置文件)
- [5. 环境变量](#5-环境变量)
- [6. 部署](#6-部署)
  - [6.1 同机：PZ 在 Docker 里](#61-同机pz-在-docker-里composebotyaml)
  - [6.2 跨机：PZ 在另一台机器的 Docker 里](#62-跨机pz-在另一台机器的-docker-里composebotremoteyaml)
  - [6.3 PZ 不在 Docker 里](#63-pz-不在-docker-里composebotnativeyaml)
  - [6.4 非 Docker 跑 Bot](#64-非-docker-跑-bot)
- [7. 本地开发与运行](#7-本地开发与运行)
- [8. 常见问题](#8-常见问题)
- [9. 目录结构](#9-目录结构)

---

## 这是什么

- **管的是谁：** 一台已经在跑的 Project Zomboid 专用服务器（ Dedicated Server）。Bot 和游戏服通过 RCON 对话，RCON 是 PZ 官方的远程控制台协议，服务器的 `servertest.ini` 里用 `RCONPort` / `RCONPassword` 打开。
- **能做什么：** 在 Discord 里用 `/players` 看在线人数、用 `/restart queue` 排一个“人走光再重启”的任务、用 `/announce` 往游戏里发公告、用 `/kick`、`/ban` 等命令做日常管理。
- **不能做什么：** 不会帮你装模组、不会改地图、不会提供一个 Web 面板、也不会直接 `docker restart` 游戏容器。
- **重启是怎么实现的：** Bot 只会发 `servermsg`（游戏内公告）→ `save`（存档）→ `quit`（让 PZ 进程自己退出）。真正把进程拉起来的，是**游戏服容器本身**的 `restart: unless-stopped`。所以 Bot 不需要 Docker 权限。

### 回复与多语言

- **Discord 侧：** 每条回复都是一条 Embed，按 `config/i18n.yaml` 里的 `discord_locales`（默认 `zh`、`en`、`jp`）分成多个字段，一次性展示多种语言。查询类（`/players`、`/restart status`）是公开消息，频道里所有人都能看见；会改动服务器的操作是“仅自己可见（ephemeral）”，只有操作者能看见结果，避免把封禁理由、SteamID 贴到公共频道。
- **游戏内：** 每条公告会按 `game_locales` 连续发多条 `servermsg`（因为 PZ 单条 `servermsg` 有长度限制，超长会自动拆成多条，不会截断）。

---

## 快速开始（5 分钟跑起来）

> 如果你已经有 Discord 机器人，直接跳到第 3 步。否则从第 1 步的“申请机器人”开始。

1. 按[第 1 章](#1-discord-机器人申请与邀请手把手)申请机器人，拿到 `DISCORD_TOKEN`，并把机器人拉进你的 Discord 服务器。
2. ⚠️ **必做 — 配置 `config/permissions.yaml`**：在 Discord 里**开启开发者模式**并复制 `guild_id` / 角色 ID（见 [3.2](#32-如何拿到-guild_idrole_iduser_idchannel_id)），填到 `config/permissions.yaml`。**首次启动前必须改这个文件**，否则机器人能上线但没有任何斜杠命令（`guilds` 为空时 Bot 会跳过同步、日志提示 `no real guild ids ... skipped`）。
   > 其他文件不用管：`config/i18n.yaml` / `config/limits.yaml` / `config/locales/*.yaml` 首次启动时会自动从镜像默认值补齐（`[entrypoint] seeding missing ...`），缺了也不会报 `missing config file`。
3. 复制环境变量文件并填好：

   ```bash
   cp .env.example .env
   # 用编辑器打开 .env，填 DISCORD_TOKEN / RCON_HOST / RCON_PORT / RCON_PASSWORD
   # 只有「PZ 容器和 Bot 在同一台机器」才需要 BOT_NETWORK（见第 6 章选表）
   ```

4. 按拓扑选一个 compose 文件启动（不要三个一起起）：

   ```bash
   # 同机 Docker（最常见）
   docker compose -f compose.bot.yaml up -d
   docker compose -f compose.bot.yaml logs -f pz-bot

   # 跨机 Docker：     -f compose.bot.remote.yaml
   # PZ 不在 Docker：  -f compose.bot.native.yaml
   ```

5. 去 Discord 频道打 `/players` 试试。如果能看到人数，说明 RCON 已通。

---

## 1. Discord 机器人申请与邀请（手把手）

> 官方文档：[Discord Developer Portal — Applications](https://discord.com/developers/applications) · [discord.py 文档](https://discordpy.readthedocs.io/en/stable/)

### 1.1 创建 Application

1. 打开 <https://discord.com/developers/applications>，点 **New Application**，起个名字（比如 `PZ-Bot`），创建。
2. 左侧进入 **General Information**，记下 **Application ID**（就是 `client_id`，邀请链接要用）。

### 1.2 创建 Bot 并拿到 Token

1. 左侧进入 **Bot**，点 **Add Bot**（如果已存在则直接看下一步）。
2. 在 **Token** 区域点 **Reset Token**（首次是 **Copy**），复制生成的 Token。**这就是 `.env` 里的 `DISCORD_TOKEN`，不要贴到公开频道或提交到 git。**
3. **Privileged Gateway Intents**：本项目**不需要**开 `Presence Intent` / `Server Members Intent` / `Message Content`。保持默认关闭即可（代码里只用了 `Intents.default()`）。
4. 把 Token 粘到 `.env`：

   ```
   DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OTA.GhIjKl.MnOpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUv
   ```

### 1.3 生成邀请链接

1. 左侧进入 **OAuth2 → URL Generator**。
2. **Scopes** 勾选：
   - `bot`
   - `applications.commands`（没有这个，斜杠命令不会出现）
3. 下方 **Bot Permissions** 勾选（最小可用）：
   - `Send Messages`（发消息）
   - `Embed Links`（发 Embed）
   - `Read Message History`（可选，便于看历史）
   - 不需要 `Administrator`。
4. 复制下方生成的 **Generated URL**，形如：

   ```
   https://discord.com/api/oauth2/authorize?client_id=123456789012345678&permissions=274877908032&scope=bot%20applications.commands
   ```

   把 `123456789012345678` 换成你的 **Application ID** 即可。`permissions` 数值是上一步勾选的权限算出来的，不用手算，用页面生成的就行。

### 1.4 把机器人拉进服务器

1. 用管理员账号在浏览器打开上一步的邀请链接。
2. 选择你要管理的 Discord 服务器，点 **Authorize**，完成人机验证。
3. 回到 Discord，你会在成员列表看到机器人上线（灰色离线是因为还没启动容器，启动后会变绿）。

### 1.5 Token 保管

- Token 等同密码。泄露后立刻回 **Developer Portal → Bot → Reset Token**，并更新 `.env` 后重启容器：`docker compose -f compose.bot.yaml restart pz-bot`。
- 本项目所有密钥只走环境变量，不会写进 `config/*.yaml`，也不会打进镜像。

---

## 2. 支持的命令

> 斜杠命令只会同步到 `config/permissions.yaml` 里列出的服务器（`guilds` 的 key）。没列出的服务器看不到任何命令。私信里也不能用。
>
> 所有需要 RCON 的命令都会在 3 秒内先 `defer`（显示“Bot 正在思考…”），再去连游戏服，避免 Discord 超时。
>
> **自动补全：** 凡是参数名为 `player` 的，都支持按在线名单自动补全。你可以打字触发补全，也可以直接手打完整角色名。重名时会提示你输入完整名字，不会“猜一个”。

### 2.1 查询与重启（最常用）

| 命令 | 参数 | 说明 | 默认最低权限 | 回复可见性 | 需要二次确认 |
|---|---|---|---|---|---|
| `/players` | 无 | 显示当前在线人数和名单。会刷新缓存，供其他命令的自动补全使用。 | C（所有人） | 公开 | 否 |
| `/restart queue` | 无 | 排一个“空服再重启”的任务。有人在线就等着，每 `POLL_INTERVAL`（默认 30s）查一次 `players`；人数归零后会**再等 `EMPTY_CONFIRM_SECONDS`（默认 10s）二次确认**，两次都为 0 才发游戏内公告 → `save` → `quit`。超时（`RESTART_TIMEOUT` 默认 7200s）只取消，不会强制退出。 | B | 仅自己 | 否 |
| `/restart cancel` | 无 | 取消当前排队。B 只能取消自己的；A 可以取消任何人的。 | B（实际按“谁建的”再校验） | 仅自己 | 否 |
| `/restart status` | 无 | 看队列状态或重启窗口剩余时间。公开消息，频道里所有人都能查。 | B | 公开 | 否 |
| `/restart now` | 无 | 不等人，直接发公告 → `save` → `quit`。如果当前有排队，会先取消排队再执行。 | A | 仅自己 | **是**（30s 内点 Confirm/Cancel，只有发起人能点） |

**重启时的游戏内喊话：** `queue` 成功时会按 `game_locales` 连续发一次“已排队”；真正要 `save`/`quit` 前会再连续发一次“即将重启”；`now` 只发执行前那一次。超时或被人取消则不往游戏里喊，避免刷屏。排队过程中不会每隔几分钟刷一次。

**重启窗口：** 发出 `save`/`quit` 后会进入 `RestartingWindow`（`RESTART_GRACE` 默认 360s，约 6 分钟，适配本项目的 PZ 冷启动时间）。窗口内除 `/restart status` 外的所有命令都会被拒绝，并告诉你还剩多少秒。窗口结束后如果 RCON 仍不通，就按普通 RCON 失败处理。

### 2.2 基础运维

| 命令 | 参数 | 说明 | 默认最低权限 | 回复可见性 | 需要二次确认 |
|---|---|---|---|---|---|
| `/announce` | `message`: 文本（必填） | 把你输入的文字**原样**按每种 `game_locales` 各发一条 `servermsg`。不会做翻译，输入什么发什么。超长按 `servermsg_max_chars`（默认 200）自动拆条。 | A | 仅自己 | 否 |
| `/save` | 无 | 只存档，不重启。 | A | 仅自己 | 否 |

### 2.3 会话管理（踢人、封禁、白名单、权限）

| 命令 | 参数 | 说明 | 默认最低权限 | 回复可见性 | 需要二次确认 |
|---|---|---|---|---|---|
| `/kick` | `player`: 角色名（必填，支持自动补全）<br>`reason`: 原因（选填） | 踢出一个在线玩家。对应 RCON `kickuser`。 | A | 仅自己 | **是** |
| `/ban user` | `player`: 角色名（必填） | 按角色名封禁。对应 `banuser`。 | A | 仅自己 | **是** |
| `/ban steamid` | `steamid`: SteamID 字符串（必填） | 按 SteamID 封禁。对应 `banid`。离线也能封。 | A | 仅自己 | **是** |
| `/unban user` | `player`: 角色名（必填） | 按角色名解封。对应 `unbanuser`。 | A | 仅自己 | **是** |
| `/unban steamid` | `steamid`: SteamID 字符串（必填） | 按 SteamID 解封。对应 `unbanid`。 | A | 仅自己 | **是** |
| `/whitelist add` | `player`: 账号名（必填）<br>`password`: 白名单密码（必填） | 把账号加入白名单。对应 `adduser`。 | A | 仅自己 | 否 |
| `/whitelist remove` | `player`: 账号名（必填） | 把账号移出白名单。对应 `removeuserfromwhitelist`。 | A | 仅自己 | **是** |
| `/access set` | `player`: 角色名（必填，自动补全）<br>`level`: 权限等级（必选，下拉：`none` / `observer` / `gm` / `overseer` / `moderator` / `admin`） | 改游戏内权限等级。对应 `setaccesslevel`。**破窗保护：** 如果目标当前已经是 `admin`，只有 `break_glass_user_ids` 白名单里的 Discord 用户才能改；白名单为空时，禁止改任何已是 `admin` 的人（只能把非 admin 往上提）。 | A（再叠加破窗校验） | 仅自己 | **是** |

### 2.4 传送、给予、尸潮、玩家状态

| 命令 | 参数 | 说明 | 默认最低权限 | 回复可见性 | 需要二次确认 |
|---|---|---|---|---|---|
| `/teleport to-player` | `player`: 要被传送的人（必填）<br>`target`: 传送目标玩家（必填） | 把 `player` 传到 `target` 身边。对应 `teleport`。 | A | 仅自己 | 否 |
| `/teleport to-coords` | `player`: 角色名（必填）<br>`x` / `y` / `z`: 整数坐标（必填） | 把玩家传到指定坐标。对应 `teleportto`。 | A | 仅自己 | 否 |
| `/give item` | `player`: 角色名（必填）<br>`item`: 物品脚本名，如 `Base.Axe`（必填）<br>`count`: 数量（选填，默认 1，范围见 `limits.yaml`） | 给玩家物品。对应 `additem`。脚本名写错会直接返回 RCON 原文。 | A | 仅自己 | 否 |
| `/give xp` | `player`: 角色名（必填）<br>`perk`: 技能名，如 `Woodwork`（必填）<br>`amount`: 经验值（必填，范围见 `limits.yaml`） | 给玩家技能经验。对应 `addxp`。 | A | 仅自己 | 否 |
| `/give vehicle` | `player`: 角色名（必填）<br>`script`: 载具脚本名（必填） | 在玩家附近刷一辆车。对应 `addvehicle`。 | A | 仅自己 | 否 |
| `/horde` | `player`: 角色名（必填）<br>`count`: 数量（必填，范围见 `limits.yaml`） | 在玩家附近刷一波僵尸。对应 `createhorde`。 | A | 仅自己 | 否 |
| `/player god` | `player`: 角色名（必填） | 切换上帝模式。对应 `godmode`。 | A | 仅自己 | 否 |
| `/player invisible` | `player`: 角色名（必填） | 切换隐身。对应 `invisible`。 | A | 仅自己 | 否 |
| `/player noclip` | `player`: 角色名（必填） | 切换穿墙。对应 `noclip`。 | A | 仅自己 | 否 |

> **数量上限**在 `config/limits.yaml` 里配，热加载生效：`item 1–50`、`xp 1–100000`、`horde 1–50`、`vehicle` 固定 1。超限会直接拒绝，不会“截断后执行”。

### 2.5 天气与事件

| 命令 | 参数 | 说明 | 默认最低权限 | 回复可见性 | 需要二次确认 |
|---|---|---|---|---|---|
| `/weather start-rain` | 无 | 开始下雨。对应 `startrain`。 | A | 仅自己 | 否 |
| `/weather stop-rain` | 无 | 停止下雨。对应 `stoprain`。 | A | 仅自己 | 否 |
| `/weather thunder` | 无 | 触发雷电。对应 `thunder`。 | A | 仅自己 | 否 |
| `/weather chopper` | 无 | 触发直升机事件。对应 `chopper`。 | A | 仅自己 | 否 |
| `/weather gunshot` | 无 | 触发枪声事件。对应 `gunshot`。 | A | 仅自己 | 否 |

> “谋杀谜语人”说明：上面表格里每一行的“参数”都写了**参数名、类型、是否必填**；“说明”里写了**它到底做什么、对应哪条 RCON、会不会有二次确认**。不会出现“自行体会”这种话。

---

## 3. 权限管理

### 3.1 什么是 `guild_id` / `role_id` / `user_id` / `channel_id`

- **Guild** 就是**一个 Discord 服务器**。Discord API 里把“服务器”叫 `guild`，所以配置文件里的 `guild_id` 就是“你的 Discord 服务器的 ID”。
- **Role / User / Channel ID** 同理，都是 Discord 的**雪花 ID（snowflake）**——一串很长的数字字符串，比如 `"123456789012345678"`。不要填角色名字，填 ID。
- 为什么用 ID 而不用名字？因为角色可以改名，改名后按名字匹配会“悄悄掉权”；ID 永远不变。

### 3.2 如何拿到 `guild_id` / `role_id` / `user_id` / `channel_id`

1. 在 Discord 客户端：**设置 → 高级 → 打开“开发者模式”（Developer Mode）**。
   - 桌面端：左下角齿轮 → 高级。
   - 手机端：设置 → 高级。
2. 回到服务器：
   - **服务器 ID（`guild_id`）：** 右键服务器图标 → **复制 ID**。
   - **角色 ID（`role_id`）：** 服务器设置 → 身份组 → 右键某个身份组 → **复制 ID**。
   - **用户 ID（`user_id`）：** 右键某个成员 → **复制 ID**。
   - **频道 ID（`channel_id`）：** 右键某个频道 → **复制 ID**。
3. 把复制到的数字**用引号包起来**填进 `config/permissions.yaml`。不要漏引号，YAML 会把大数字当成科学计数法。

### 3.3 三档权限（Tier）

| 档位 | 对应字段 | 典型人群 | 默认能做什么 |
|---|---|---|---|
| **A** | `admin_role_ids` | 服主 / 管理组 | 全部命令；可以取消任何人的 `/restart queue`；可以执行 `/restart now` |
| **B** | `member_role_ids` | 僵毁玩家 / `@pz` 身份组 | `/players` + `/restart queue` + `/restart status`；只能取消**自己**建的排队 |
| **C** | 不在 A/B 里的所有人 | 普通成员 / `@everyone` | 仅 `/players` |

- 一个人如果同时有 A 和 B 的身份组，**取最高档（A）**。
- 默认矩阵在代码 `bot/constants.py` 的 `DEFAULT_MIN_TIER` 里定义；`permissions.yaml` 的 `command_min_tier` 可以把单条命令的最低档改低（比如让 B 也能 `/announce`），不需要改代码。

### 3.4 `config/permissions.yaml` 示例（可直接复制去改）

```yaml
# 只有写在这里的服务器才会收到斜杠命令。新增服务器后要重启 Bot（见 6.1）。
guilds:
  # 你的 Discord 服务器 ID（右键服务器图标 → 复制 ID）
  "123456789012345678":
    # Tier-A：服主 / 管理组。给 1–2 个最可信的身份组即可
    admin_role_ids:
      - "111111111111111111"   # @Admin
      - "222222222222222222"   # @Moderator（如果你想让协管也能管）

    # Tier-B：普通僵毁玩家。拥有这个身份组的人可以排队重启
    member_role_ids:
      - "333333333333333333"   # @pz / @Survivor

    # （可选）只允许在这些频道使用命令。空列表表示“本服务器任意频道都能用”
    command_channel_ids: []
    # 例子：只允许在 #pz-ops 里用
    # command_channel_ids:
    #   - "444444444444444444"

    # （可选）破窗白名单：允许改“已经是游戏内 admin 的玩家”的 Discord 用户 ID
    # 为空表示“禁止改任何已是 admin 的人，只能把非 admin 往上提”
    break_glass_user_ids:
      - "555555555555555555"   # 服主的 Discord 用户 ID

    # （可选）单条命令的最低档覆盖。key 必须在下面的白名单里
    command_min_tier:
      # 让 B 也能发公告
      # announce: B
      # 让所有人都能看状态（默认 B 才能看，这里改成 C）
      # restart_status: C

    # 合法的覆盖 key（改错会启动失败）：
    # players, restart_queue, restart_cancel, restart_status, restart_now,
    # announce, save, kick, ban, unban, whitelist, access,
    # teleport, give, horde, player, weather
```

**字段解释：**

- `admin_role_ids` / `member_role_ids`：字符串数组，填角色 ID。漏填或填错 ID 会导致“明明有身份组却提示权限不足”。
- `command_channel_ids`：字符串数组，填频道 ID。空数组 = 不限频道；填了就只在这些频道接受命令，其他频道会回“请在指定频道使用”。
- `break_glass_user_ids`：字符串数组，填用户 ID。用于 `/access set` 的破窗保护（见 2.3）。
- `command_min_tier`：对象，key 是命令 key（见上例注释），value 只能是 `A` / `B` / `C`（大小写不敏感）。

### 3.5 热加载与新增服务器

- **改角色、改 `command_min_tier`、改 `command_channel_ids`、改 `break_glass_user_ids`：** 直接改 `config/permissions.yaml`，**下一次命令就会生效**（Bot 会按文件 `mtime` 热加载，坏文件会自动保留上一份好配置并打日志）。
- **新增/删除服务器（改 `guilds` 的 key）：** 斜杠命令的注册只在 **Bot 启动时**对 `guilds` 里的每个 key 做 `sync`。所以新增服务器后要：

  ```bash
  docker compose -f compose.bot.yaml restart pz-bot
  # 或非 Docker：systemctl restart pz-discord-bot
  ```

- 未列入 `guilds` 的服务器：看不到任何斜杠命令；私信里也用不了。

---

## 4. 配置文件

| 文件 | 作用 | 热加载 | 改错会怎样 |
|---|---|---|---|
| `config/permissions.yaml` | 权限与频道白名单（见上章） | 是（角色/频道/覆盖立即生效；新增 guild 需重启） | 启动失败或保留上一份好配置 |
| `config/i18n.yaml` | 多语言开关 | 是 | 启动失败 |
| `config/limits.yaml` | 数值上限与杂项 | 是 | 启动失败 |
| `config/locales/zh.yaml` `en.yaml` `jp.yaml` | 文案包（错误提示、确认文案、人数文案等） | 是 | 启动失败 |

### 4.1 `config/i18n.yaml`

```yaml
# 一条 Discord 回复里按这些语言各占一个 Embed 字段
discord_locales:
  - zh
  - en
  - jp
# 游戏内按这些语言连续各发一条 servermsg
game_locales:
  - zh
  - en
  - jp
```

- 斜杠命令的名字和选项名固定是英文（Discord 限制）。
- 不会按“操作者的 Discord 客户端语言”自动切换；按这份文件的列表来。
- 支持的语言：`zh`、`en`、`jp`，顺序即展示顺序。

### 4.2 `config/limits.yaml`

```yaml
item_count:
  min: 1
  max: 50
xp:
  min: 1
  max: 100000
vehicle: 1          # 固定 1，改了也按 1 处理
horde:
  min: 1
  max: 50
servermsg_max_chars: 200   # 单条 servermsg 最大字符（超长自动拆条）
confirm_timeout_seconds: 30
```

---

## 5. 环境变量

> 复制 `.env.example` 为 `.env` 再填。不要把 `.env` 提交到 git。

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `DISCORD_TOKEN` | **是** | 无 | 机器人 Token（见 1.2） |
| `RCON_HOST` | **是** | 无 | PZ 的 RCON 主机。填什么取决于拓扑，见 [第 6 章选表](#6-部署)。**无默认值，必须手写。** |
| `RCON_PORT` | **是** | 无 | RCON 端口（PZ 默认 27015，但以你 `servertest.ini` 的 `RCONPort` 为准） |
| `RCON_PASSWORD` | **是** | 无 | RCON 密码（`RCONPassword`） |
| `BOT_NETWORK` | **仅** [compose.bot.yaml](compose.bot.yaml) 必填 | 无 | 已有 PZ 容器所在的 **external** Docker 网络名。Python 进程不读这个变量；跨机 / 原生拓扑不要填也没关系 |
| `POLL_INTERVAL` | 否 | `30` | 排队时每隔多少秒查一次 `players` |
| `RESTART_TIMEOUT` | 否 | `7200` | 排队超时秒数，到点只取消不 `quit` |
| `RESTART_GRACE` | 否 | `360` | `save`+`quit` 后的宽限秒数（本项目按实测冷启动约 6 分钟） |
| `RCON_FAIL_THRESHOLD` | 否 | `3` | 排队时连续 RCON 失败多少次后取消排队 |
| `EMPTY_CONFIRM_SECONDS` | 否 | `10` | 空服二次确认的间隔秒数 |
| `RCON_TIMEOUT` | 否 | `10` | 单次 RCON 超时秒数 |
| `CONFIG_DIR` | 否 | `config`（容器内 `/app/config`） | 配置目录 |
| `HEALTH_STATE_PATH` | 否 | `/tmp/pz-bot-health.json` | 健康状态文件（用于区分“计划内重启”与“真挂了”） |
| `LOG_LEVEL` | 否 | `INFO` | 日志级别：`DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## 6. 部署

本仓库只交付 **Bot**。游戏服假定已经在某台机器上跑着——可能是 Docker 容器，也可能是裸进程。三个 compose 文件对应三种拓扑，**一次只起其中一个**，服务名都是 `pz-bot`，镜像都是 `rainbreath/pz-discord-bot:latest`。

| 你的情况 | 用哪个文件 | `RCON_HOST` 填什么 | 要不要 `BOT_NETWORK` |
|---|---|---|---|
| PZ 是 Docker 容器，**和 Bot 同一台机器** | [compose.bot.yaml](compose.bot.yaml) | PZ 的 compose **服务名**（如 `pz-server`） | **要** |
| PZ 是 Docker 容器，**在另一台机器** | [compose.bot.remote.yaml](compose.bot.remote.yaml) | PZ 那台机器的 **内网 IP**（如 `10.0.0.5`） | 不要 |
| PZ **不在 Docker 里**（裸进程 / systemd） | [compose.bot.native.yaml](compose.bot.native.yaml) | 同机用 `host.docker.internal`；跨机用内网 IP | 不要 |

三个文件的共同点（已经写好，不用你再改）：

- 只有 `pz-bot` 一个服务，不会再起一个游戏服。
- `restart: unless-stopped`。
- `volumes: ./config:/app/config` —— 改 YAML 不用 rebuild。
- `logging: json-file, max-size 10m, max-file 5`。
- `healthcheck: python -m bot.health` —— RCON 通 **或** 处于计划内重启窗口即 healthy；`unhealthy` 不会杀容器；`start_period` 与 `RESTART_GRACE` 对齐（360s）。
- **不挂 `docker.sock`**，Bot 这边也**不把 RCON 端口映到宿主机**。

重启机制不变：Bot 只发 `servermsg` → `save` → `quit`。把进程拉起来的是游戏服自己（容器的 `restart: unless-stopped`，或你给裸进程配的 systemd / 看门狗）。

日常操作把下面命令里的文件名换成你选的那个即可：

```bash
docker compose -f compose.bot.yaml restart pz-bot   # 改了 guild 列表后必须重启
docker compose -f compose.bot.yaml down
docker compose -f compose.bot.yaml logs -f pz-bot
docker inspect --format='{{json .State.Health}}' pz-discord-bot-pz-bot-1 | python -m json.tool
```

---

### 6.1 同机：PZ 在 Docker 里（`compose.bot.yaml`）

> 最常见、也最安全。Bot 加入已有 PZ 网络，RCON 全程走 Docker 内部 DNS，**不要把 RCON 端口映射到宿主机或公网**。

**第 1 步：查出 PZ 所在网络名**

```bash
docker network ls
# 常见名字：pz_default、pz-server_default、或你自定义的 pz-net
docker inspect <pz-server-容器名> --format '{{json .NetworkSettings.Networks}}' | python -m json.tool
```

把网络名记下来，填到 `.env` 的 `BOT_NETWORK`。

**第 2 步：准备 `.env` 与 `config/permissions.yaml`**

```bash
cp .env.example .env
# 编辑 .env：
#   DISCORD_TOKEN=...
#   RCON_HOST=pz-server          # PZ 的 compose 服务名，不是 localhost
#   RCON_PORT=27015              # 以 servertest.ini 的 RCONPort 为准
#   RCON_PASSWORD=...
#   BOT_NETWORK=pz_default       # 上一步查到的网络名
# 编辑 config/permissions.yaml：把 000… 换成真实 guild_id / role_id
```

`RCON_HOST` 填服务名（Docker 内部 DNS 能解析），**不要填 `localhost`**——那是 Bot 容器自己的回环，连不到隔壁容器。

**第 3 步：启动**

```bash
docker compose -f compose.bot.yaml up -d
docker compose -f compose.bot.yaml logs -f pz-bot
# 看到 "synced slash commands" 和 "bot ready" 即成功
```

这个文件会要求 `BOT_NETWORK`：没填 compose 会直接拒绝启动。网络必须已经存在（`external: true`），compose **不会**帮你新建一个。

---

### 6.2 跨机：PZ 在另一台机器的 Docker 里（`compose.bot.remote.yaml`）

> Bot 加不进另一台机器的 Docker 网络，只能走局域网打 RCON。`BOT_NETWORK` 用不上，Python 进程也不读它。

**在 PZ 那台机器上（不是本仓库）**，必须把 RCON **只绑到内网 IP**，不要绑 `0.0.0.0`：

```yaml
# 这是已有 pz-server 的 compose 片段，不在本仓库里
ports:
  - "10.0.0.5:27015:27015"    # 宿主机内网IP:宿主机端口:容器端口
# 不要写成 "27015:27015"（那会绑到 0.0.0.0，等于对公网开门）
```

防火墙只放行 Bot 那台机器的源 IP，例如：

```bash
# 在 PZ 主机上，只允许 Bot 主机 10.0.0.8 访问 27015
sudo ufw allow from 10.0.0.8 to any port 27015 proto tcp
```

**在跑 Bot 的这台机器上：**

```bash
cp .env.example .env
# 编辑 .env：
#   DISCORD_TOKEN=...
#   RCON_HOST=10.0.0.5          # PZ 宿主机的内网 IP，不是服务名，也尽量不要用公网 IP
#   RCON_PORT=27015             # 上一步映射出来的宿主机端口
#   RCON_PASSWORD=...
#   BOT_NETWORK 可以留空

docker compose -f compose.bot.remote.yaml up -d
docker compose -f compose.bot.remote.yaml logs -f pz-bot
```

这个文件**没有** `networks:` 段，也**没有**端口映射。重启仍然靠 PZ 容器自己的 `restart: unless-stopped`；Bot 不会、也不能去另一台机器上 `docker restart`。

连通性自检（在 Bot 宿主机上）：

```bash
# 能通再启动 Bot，省得对着防火墙空转
nc -vz 10.0.0.5 27015
# 或：python -c "import socket; s=socket.create_connection(('10.0.0.5',27015),5); print('ok'); s.close()"
```

---

### 6.3 PZ 不在 Docker 里（`compose.bot.native.yaml`）

> PZ 是裸进程（官方 dedicated、steamcmd、systemd 服务等）。没有 Docker 网络可加入。Bot 容器要通过宿主机才能打到 RCON。

**`RCON_HOST` 怎么填：**

| PZ 在哪 | `RCON_HOST` |
|---|---|
| 和 Bot **同一台机器** | `host.docker.internal`（compose 已加 `extra_hosts: host.docker.internal:host-gateway`） |
| 在**另一台机器** | 那台机器的内网 IP（网络路径和 6.2 一样） |

**关键限制：** 容器看不见宿主机的 `127.0.0.1`。如果 PZ 的 RCON 只绑在 `127.0.0.1`，`host.docker.internal` 也连不上。二选一：

1. 把 PZ 的 RCON 绑到 `0.0.0.0` 或内网网卡，再用防火墙只放行 Docker 网桥 / Bot 主机，然后用 `host.docker.internal`。
2. **仅 Linux**：打开 [compose.bot.native.yaml](compose.bot.native.yaml) 里注释掉的 `network_mode: host`，设 `RCON_HOST=127.0.0.1`，并删掉 `extra_hosts`。Docker Desktop（Windows / macOS）没有真正的 host 网络，这条路走不通。

**在跑 Bot 的这台机器上：**

```bash
cp .env.example .env
# 编辑 .env：
#   DISCORD_TOKEN=...
#   RCON_HOST=host.docker.internal   # 同机；跨机改成 10.0.0.5
#   RCON_PORT=27015
#   RCON_PASSWORD=...
#   BOT_NETWORK 可以留空

docker compose -f compose.bot.native.yaml up -d
docker compose -f compose.bot.native.yaml logs -f pz-bot
```

重启责任在你这边：Bot 仍然只发 `servermsg` → `save` → `quit`。裸进程没有 `restart: unless-stopped`，需要你自己用 systemd / 看门狗把 PZ 拉起来，否则 `/restart` 之后游戏服不会回来。

---

### 6.4 非 Docker 跑 Bot

> Bot 自己也不进容器，直接跑在宿主机或另一台机器上。三种 PZ 拓扑都能用这一节，只是 `RCON_HOST` 不同。

**第 1 步：准备 Python 环境**

```bash
# 需要 Python 3.12+
python3 --version

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**第 2 步：准备配置文件与环境变量**

```bash
cp .env.example .env
# BOT_NETWORK 不需要（那是 compose.bot.yaml 专用）
# RCON_HOST：
#   PZ 同机裸进程 / 同机 Docker 把端口映到了 127.0.0.1 → 127.0.0.1
#   PZ 在另一台机器                                 → 内网 IP
# 其余变量同上
```

你也可以不用 `.env` 文件，直接在 shell 里 `export`：

```bash
export DISCORD_TOKEN=...
export RCON_HOST=127.0.0.1
export RCON_PORT=27015
export RCON_PASSWORD=...
export CONFIG_DIR=$(pwd)/config
```

**第 3 步：直接运行（前台）**

```bash
# 方式 A：用 .env 文件（本项目不捆绑 python-dotenv，需要手动 export）
export $(cat .env | xargs)   # 仅当 .env 里没有空格/引号时可用
python -m bot

# 方式 B：直接在命令行带环境变量
DISCORD_TOKEN=... RCON_HOST=127.0.0.1 RCON_PORT=27015 RCON_PASSWORD=... python -m bot
```

看到 `bot ready` 即成功。按 `Ctrl+C` 退出。

**第 4 步：用 systemd 常驻（Linux）**

创建 `/etc/systemd/system/pz-discord-bot.service`：

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
# 可选：把日志打到 journald
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

然后：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pz-discord-bot
sudo systemctl status pz-discord-bot
sudo journalctl -u pz-discord-bot -f
```

**健康检查（非 Docker）：**

```bash
# 和 Docker healthcheck 跑的是同一个入口
python -m bot.health; echo $?
# 0 = healthy，1 = unhealthy
```

---

## 7. 本地开发与运行

### 7.1 环境准备

```bash
python3 --version   # 要求 3.12+
python -m venv .venv
source .venv/bin/activate   # Windows Git Bash: source .venv/Scripts/activate
                            # Windows CMD:      .venv\Scripts\activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` 会额外装 `pytest` / `pytest-asyncio`。

### 7.2 配置与启动（开发）

```bash
cp .env.example .env
# 填好 DISCORD_TOKEN / RCON_HOST / RCON_PORT / RCON_PASSWORD
# 本地开发时建议直接用非 Docker 方式（见 6.4），不用填 BOT_NETWORK
# 建议先在测试用 Discord 服务器上试，permissions.yaml 里只放测试服的 guild_id

python -m bot
# 或带环境变量一次性启动：
# DISCORD_TOKEN=... RCON_HOST=... RCON_PORT=... RCON_PASSWORD=... python -m bot
```

- 首次启动会在日志里看到 `synced slash commands`（同步斜杠命令到 `permissions.yaml` 里的每个 guild）。
- 斜杠命令有缓存，Discord 侧最多 1 小时才刷新；**测试时**可尝试踢掉重邀或等一会儿。

### 7.3 跑测试

```bash
pytest -q
# 或详细
pytest -v
```

测试覆盖：权限矩阵、热加载、i18n 拆条、`players` 解析、重启队列状态机（入队/拒绝/超时/二次确认/抢占/连续失败等）、健康状态。

### 7.4 看日志

- 本地：直接看终端的 `stdout` JSON 行（`ts` / `level` / `msg` / `operator` / `rcon_cmd` / `queue_state` 等字段）。
- Docker：`docker compose -f compose.bot.yaml logs -f pz-bot`（跨机 / 原生拓扑把文件名换成 `compose.bot.remote.yaml` / `compose.bot.native.yaml`）。
- systemd：`journalctl -u pz-discord-bot -f`。

---

## 8. 常见问题

**Q: 斜杠命令不出现？**

- 确认邀请链接勾了 `applications.commands`。
- 确认 `config/permissions.yaml` 里有你的 `guild_id`（右键服务器图标 → 复制 ID），且格式是带引号的字符串。
- 确认 Bot 已重启（`docker compose -f compose.bot.yaml restart pz-bot`），日志里有 `synced slash commands`。
- Discord 有缓存，最多等 1 小时；可尝试把 Bot 踢出后重邀。

**Q: 提示“权限不足”？**

- 确认你的账号确实拥有 `admin_role_ids` 或 `member_role_ids` 里的身份组（右键身份组 → 复制 ID 再核对）。
- 检查 `command_min_tier` 是否把该命令的最低档改高了。
- 检查 `command_channel_ids` 是否限制了频道。

**Q: 提示“服务器正在重启，约剩余 N 秒”？**

- 这是正常的 `RestartingWindow`（默认 360s）。刚执行过 `save`/`quit` 后，除 `/restart status` 外都会被挡住，避免对着已退出的 RCON 端口空转。等窗口结束即可。

**Q: RCON 失败？**

- 检查 `RCON_HOST` / `RCON_PORT` / `RCON_PASSWORD` 是否与 PZ 的 `servertest.ini` 一致。
- 同机 Docker（`compose.bot.yaml`）：`RCON_HOST` 填服务名（如 `pz-server`），不要填 `localhost`；确认 `BOT_NETWORK` 与 PZ 容器在同一网络。
- 跨机 Docker（`compose.bot.remote.yaml`）：`RCON_HOST` 填 PZ 宿主机内网 IP；确认 PZ 那边只把 RCON 映到了内网，防火墙只放行 Bot 主机。
- 原生 PZ（`compose.bot.native.yaml`）：同机填 `host.docker.internal`，不要填 `127.0.0.1`（那是 Bot 容器自己）；跨机填内网 IP。
- 非 Docker 跑 Bot：确认防火墙放行了 RCON 端口，且 RCON 只监听了内网或 `127.0.0.1`（不要暴露到公网）。
- 看日志里的 `rcon_cmd` 与 `detail` 字段。

**Q: 改了 `permissions.yaml` 不生效？**

- 改角色/频道/覆盖：下一次命令就会生效（热加载）。
- 新增/删除服务器（改 `guilds` 的 key）：必须重启 Bot。

**Q: 改了 `permissions.yaml` 后 Bot 启动失败？**

- YAML 语法错或 key 写错（如 `command_min_tier` 的 key 不在白名单）会导致启动失败。运行时改错则会保留上一份好配置并打 `error` 日志，不会把权限打成“全员 C”或“全员 A”。

---

## 9. 目录结构

```
.
├── bot/                 # Python 包（discord.py + RCON + 队列 + 权限 + i18n）
│   ├── app.py           # 建 Bot、注册 Cog、按 guild 同步斜杠命令
│   ├── settings.py      # 环境变量
│   ├── config.py        # YAML 加载与 mtime 热加载
│   ├── permissions.py   # 三档 Tier 与频道/破窗校验
│   ├── rcon_client.py   # async Source RCON 封装与 players 解析
│   ├── restart_queue.py # 全局 RestartQueue 状态机
│   ├── discord_util.py  # 权限门禁、Embed、多语言、确认按钮
│   └── cogs/            # 斜杠命令分组
├── config/
│   ├── permissions.yaml
│   ├── i18n.yaml
│   ├── limits.yaml
│   └── locales/{zh,en,jp}.yaml
├── compose.bot.yaml         # 同机：PZ 容器 + Bot 同一台机器
├── compose.bot.remote.yaml  # 跨机：PZ 容器在另一台机器
├── compose.bot.native.yaml  # PZ 不在 Docker 里
├── Dockerfile
├── requirements.txt / requirements-dev.txt
└── tests/               # pytest
```

术语表见 [CONTEXT.md](CONTEXT.md)。开发过程与代码注释使用英文。
