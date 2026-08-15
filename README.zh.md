# PZ Discord Bot

Project Zomboid 专用 Discord 管理 bot。通过语义化 slash 命令调用 Source RCON。

其他语言：[English](README.en.md) · [日本語](README.jp.md)

## 做什么

- `/players` 查看在线人数
- `/restart queue|cancel|status|now` 空服排队重启或强制重启
- 管理命令：`/announce` `/save` `/kick` `/ban` `/unban` `/whitelist` `/access` `/teleport` `/give` `/horde` `/player` `/weather`
- 真正拉起游戏服靠 **已有 PZ 容器** 的 `restart: unless-stopped`（bot 只发 `servermsg` → `save` → `quit`）

## 权限三档

写在 `config/permissions.yaml`，按 Discord `guild_id` 分块，角色用雪花 ID：

| 档 | 谁 | 默认能做什么 |
|---|---|---|
| A | `admin_role_ids` | 全部命令；可取消他人队列 |
| B | `member_role_ids`（僵毁 / @pz） | `/players` + `/restart queue\|status`，只能 cancel 自己的 |
| C | 其余成员 | 仅 `/players` |

`command_min_tier` 可把单条命令最低档改成 B/C。未列入 yaml 的服务器看不到命令。私信禁用。

## 部署

本仓库只交付 `pz-bot` 镜像和 `compose.bot.yaml`。游戏服必须已经在某个 Docker 网络里。

1. 复制 `.env.example` 为 `.env`，填入：
   - `DISCORD_TOKEN`
   - `RCON_HOST` / `RCON_PORT` / `RCON_PASSWORD`（无默认值，填你现有 PZ 容器的服务名和端口）
   - `BOT_NETWORK`（已有 pz-server 所在的 **external** 网络名）
2. 编辑 `config/permissions.yaml`：把占位 `000…` 换成真实 `guild_id` 和角色 ID。
3. 按需改 `config/i18n.yaml`（`discord_locales` 与 `game_locales` 独立）和 `config/limits.yaml`。
4. 启动：

```bash
docker compose -f compose.bot.yaml up -d --build
```

Bot 邀请链接必须带 `bot` + `applications.commands`。新增 guild 后改 yaml 并 `docker compose -f compose.bot.yaml restart pz-bot`（slash 只在启动时同步）。

## 运行时行为

- 密钥只走环境变量。`./config` bind-mount 进容器，改 yaml 不必 rebuild。
- 角色档 / 最低档 / 频道白名单热加载；坏文件保留上一份好配置。
- 重启队列只在内存，超时（默认 7200s）只取消不 `quit`。`RESTART_GRACE` 默认 360s。
- Healthcheck：RCON 通，或处于计划内重启窗口，则 healthy。`unhealthy` 不杀容器。
- 日志：`json-file`，`10m × 5`。

## 本地开发

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements-dev.txt
pytest
```

开发过程与代码注释使用英文。领域词汇见 [CONTEXT.md](CONTEXT.md)。
