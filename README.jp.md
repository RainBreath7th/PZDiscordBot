# PZ Discord Bot

1 台の Project Zomboid 専用サーバーを管理する Discord bot です。意味のある slash コマンドだけが Source RCON を呼びます。

他言語：[中文](README.zh.md) · [English](README.en.md)

## できること

- `/players` — オンライン人数
- `/restart queue|cancel|status|now` — 無人時のキュー再起動、または強制再起動
- 管理コマンド：`/announce` `/save` `/kick` `/ban` `/unban` `/whitelist` `/access` `/teleport` `/give` `/horde` `/player` `/weather`
- ゲームプロセスの再起動は **既存 PZ コンテナ** の `restart: unless-stopped` に任せます。bot が送るのは `servermsg` → `save` → `quit` だけです。

## 3 つの Tier

`config/permissions.yaml` に Discord `guild_id` ごとに書きます。ロールはスノーフレーク ID です。

| Tier | 対象 | デフォルトで使えるコマンド |
|---|---|---|
| A | `admin_role_ids` | 全コマンド。他人のキューもキャンセル可 |
| B | `member_role_ids`（PZ メンバーロール） | `/players` と `/restart queue\|status`。自分のキューだけキャンセル可 |
| C | それ以外 | `/players` のみ |

`command_min_tier` で個別コマンドの最低 Tier を B/C に下げられます。yaml に無いサーバーにはコマンドを同期しません。DM は無効です。

## デプロイ

このリポジトリが渡すのは `pz-bot` イメージと `compose.bot.yaml` だけです。ゲームサーバーは既にどれかの Docker ネットワーク上にある前提です。

1. `.env.example` を `.env` にコピーして記入：
   - `DISCORD_TOKEN`
   - `RCON_HOST` / `RCON_PORT` / `RCON_PASSWORD`（デフォルトなし。既存 PZ のサービス名とポート）
   - `BOT_NETWORK`（pz-server が入っている **external** ネットワーク名）
2. `config/permissions.yaml` の `000…` を本物の `guild_id` とロール ID に置き換える。
3. 必要なら `config/i18n.yaml`（`discord_locales` と `game_locales` は独立）と `config/limits.yaml` を調整。
4. 起動：

```bash
docker compose -f compose.bot.yaml up -d --build
```

招待 URL には `bot` と `applications.commands` が必要です。guild を追加したら yaml を直し、`docker compose -f compose.bot.yaml restart pz-bot` してください（slash 同期は起動時のみ）。

## 実行時

- 秘密情報は環境変数のみ。`./config` を bind-mount するので、yaml 変更に rebuild は不要です。
- ロール対応 / 最低 Tier / チャンネル許可はホットリロード。壊れたファイルは last-good を維持します。
- RestartQueue はメモリのみ。タイムアウト（既定 7200 秒）はキャンセルするだけで `quit` しません。`RESTART_GRACE` の既定は 360 秒です。
- Healthcheck：RCON が応答するか、計画どおりの RestartingWindow 内なら healthy。`unhealthy` でもコンテナは殺しません。
- ログ：`json-file`、`10m × 5`。

## ローカル開発

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements-dev.txt
pytest
```

コードとコメントは英語です。用語は [CONTEXT.md](CONTEXT.md) を見てください。
