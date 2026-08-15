# PZ Discord Bot

> 1 台の Project Zomboid 専用サーバーを Discord から管理します。すべてのコマンドは素直な動詞（`/kick`、`/announce`）で、裏側は Source RCON です。`/raw` はなく、Docker socket にも触りません。

他言語：[中文](README.zh.md) · [English](README.en.md) · [入口](README.md)

---

## 目次

- [これは何](#これは何)
- [クイックスタート（5 分）](#クイックスタート5-分)
- [1. Discord Bot の作成と招待（手順どおり）](#1-discord-bot-の作成と招待手順どおり)
- [2. コマンド一覧](#2-コマンド一覧)
- [3. 権限管理](#3-権限管理)
- [4. 設定ファイル](#4-設定ファイル)
- [5. 環境変数](#5-環境変数)
- [6. デプロイ](#6-デプロイ)
  - [6.1 同一ホスト：PZ が Docker 内](#61-同一ホストpz-が-docker-内composebotyaml)
  - [6.2 別ホスト：PZ が別マシンの Docker 内](#62-別ホストpz-が別マシンの-docker-内composebotremoteyaml)
  - [6.3 PZ が Docker 外](#63-pz-が-docker-外composebotnativeyaml)
  - [6.4 Bot を Docker なしで動かす](#64-bot-を-docker-なしで動かす)
- [7. ローカル開発と実行](#7-ローカル開発と実行)
- [8. よくある質問](#8-よくある質問)
- [9. ディレクトリ構成](#9-ディレクトリ構成)

---

## これは何

- **対象：** すでに稼働している Project Zomboid 専用サーバー 1 台が対象です。Bot は RCON（`servertest.ini` の `RCONPort` / `RCONPassword` で有効化するリモートコンソール）でゲームサーバーと通信します。
- **できること：** Discord で `/players` を使って人数を確認したり、`/restart queue` で「誰もいなくなったら再起動」をキューしたり、`/announce` でゲーム内に告知したり、`/kick`・`/ban` などで日常運用したりできます。
- **できないこと：** Mod の導入や地図の編集、Web パネルの提供は行いません。`docker restart` でゲームコンテナを直接操作することもありません。
- **再起動の仕組み：** Bot が送信するのは `servermsg`（ゲーム内告知）→ `save` → `quit`（PZ プロセスに終了を依頼）だけです。プロセスを再起動するのは**ゲーム側コンテナ自身**の `restart: unless-stopped` ですので、Bot に Docker 権限は不要です。

### 返信と多言語

- **Discord 側：** 1 回の返信は Embed 1 件で、`config/i18n.yaml` の `discord_locales`（既定値は `zh`・`en`・`jp`）ごとにフィールドを並べて複数言語を同時表示します。参照系（`/players`・`/restart status`）は**公開**、変更系は **ephemeral（実行者だけに見える）** となりますので、BAN 理由や SteamID がチャンネルに漏れることはありません。
- **ゲーム内：** 告知は `game_locales` ごとに `servermsg` を連続送信します。1 行の `servermsg` には文字数制限（`servermsg_max_chars`、既定値は 200）がありますので、長い行は自動的に分割され、途中で切れることはありません。

---

## クイックスタート（5 分）

> すでに Bot をお持ちの場合は手順 3 から進めてください。まだお持ちでない場合は手順 1 から始めてください。

1. [第 1 章](#1-discord-bot-の作成と招待手順どおり)の手順どおりに Bot を作成し、`DISCORD_TOKEN` をコピーしてサーバーに招待します。
2. ⚠️ **必須 — `config/permissions.yaml` を編集してください**：Discord で**開発者モード**をオンにし、`guild_id` / ロール ID をコピーして（[3.2](#32-guild_id--role_id--user_id--channel_id-の取り方)を参照）`config/permissions.yaml` に記入します。**初回起動前に必ず編集してください** — 未編集のまま起動すると Bot はオンラインになりますがスラッシュコマンドが一切表示されません（`guilds` が空 → 同期がスキップされ、ログに `no real guild ids ... skipped` と出ます）。
   > 他のファイルはそのままで構いません：`config/i18n.yaml` / `config/limits.yaml` / `config/locales/*.yaml` は初回起動時にイメージ内の既定値から自動補完されます（`[entrypoint] seeding missing ...`）。ファイルがなくても `missing config file` で落ちることはありません。
3. 環境変数ファイルをコピーして記入します：

   ```bash
   cp .env.example .env
   # .env を編集：DISCORD_TOKEN / RCON_HOST / RCON_PORT / RCON_PASSWORD
   # BOT_NETWORK は「PZ コンテナと Bot が同一ホスト」のときだけ必要です（第 6 章の表を参照）
   ```

4. トポロジに合わせて compose ファイルを **1 つだけ** 起動します（3 つ同時には起動しないでください）：

   ```bash
   # 同一ホスト Docker（いちばん多い構成です）
   docker compose -f compose.bot.yaml up -d --build
   docker compose -f compose.bot.yaml logs -f pz-bot

   # 別ホスト Docker：     -f compose.bot.remote.yaml
   # PZ が Docker 外：     -f compose.bot.native.yaml
   ```

5. Discord で `/players` を実行してみてください。人数が表示されれば RCON 接続は成功です。

---

## 1. Discord Bot の作成と招待（手順どおり）

> 公式ドキュメント：[Discord Developer Portal — Applications](https://discord.com/developers/applications) · [discord.py](https://discordpy.readthedocs.io/en/stable/)

### 1.1 Application を作成します

1. <https://discord.com/developers/applications> を開き、**New Application** をクリックして名前（例 `PZ-Bot`）を入力し、作成してください。
2. **General Information** で **Application ID**（`client_id` と同じです。招待 URL で使用します）を控えてください。

### 1.2 Bot を作成し Token をコピーします

1. 左側の **Bot** を開き、**Add Bot** をクリックします（すでに存在する場合はそのまま開いてください）。
2. **Token** 欄の **Reset Token**（初回は **Copy**）をクリックし、表示された値をコピーします。**この値が `.env` の `DISCORD_TOKEN` です。公開チャンネルや git に貼り付けないでください。**
3. **Privileged Gateway Intents：** 本プロジェクトでは `Presence Intent` / `Server Members Intent` / `Message Content` は**使用しません**。オフのままで構いません（コードでは `Intents.default()` のみを使用しています）。
4. `.env` に貼り付けます：

   ```
   DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OTA.GhIjKl.MnOpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUv
   ```

### 1.3 招待 URL を作成します

1. 左側の **OAuth2 → URL Generator** を開きます。
2. **Scopes** で以下にチェックを入れてください：
   - `bot`
   - `applications.commands`（これがないとスラッシュコマンドが表示されません）
3. 下の **Bot Permissions** で最低限以下にチェックを入れてください：
   - `Send Messages`
   - `Embed Links`
   - `Read Message History`（任意ですが、あると便利です）
   - `Administrator` は不要です。
4. 下に表示される **Generated URL** をコピーします。例：

   ```
   https://discord.com/api/oauth2/authorize?client_id=123456789012345678&permissions=274877908032&scope=bot%20applications.commands
   ```

   `123456789012345678` をご自身の **Application ID** に置き換えてください。`permissions` の数値はチェック内容から自動計算されますので、手計算する必要はありません。

### 1.4 サーバーに招待します

1. サーバー管理者のアカウントで上記 URL をブラウザで開きます。
2. 対象サーバーを選択し **Authorize** をクリックして認証を完了してください。
3. Discord に戻るとメンバー一覧に Bot が表示されます（コンテナ起動前はオフライン表示、起動後にオンラインになります）。

### 1.5 Token を安全に保管します

- Token はパスワードと同等です。万が一漏洩した場合は **Developer Portal → Bot → Reset Token** ですぐに再発行し、`.env` を更新して再起動してください：`docker compose -f compose.bot.yaml restart pz-bot`。
- 秘密情報は環境変数でのみ管理します。`config/*.yaml` やイメージ内に含めることはありません。

---

## 2. コマンド一覧

> スラッシュコマンドは `config/permissions.yaml` の `guilds` に列挙されたサーバーにだけ同期されます。登録されていないサーバーでは何も表示されず、DM でも使用できません。
>
> RCON を使用するコマンドは 3 秒以内に `defer`（「考え中…」）してからゲームに接続しますので、Discord のタイムアウトになることはありません。
>
> **補完：** `player` という引数はオンライン一覧から自動補完されます。候補を選んでいただいても、フルネームを手入力していただいても構いません。曖昧な名前は候補一覧とともに拒否され、Bot が勝手に推測することはありません。

### 2.1 参照と再起動（最重要）

| コマンド | 引数 | 説明 | 既定の最低 Tier | 公開範囲 | 要確認 |
|---|---|---|---|---|---|
| `/players` | なし | オンライン人数と名前を表示します。補完用のキャッシュも更新します。 | C（全員） | 公開 | 不要 |
| `/restart queue` | なし | 「無人になったら再起動」をキューします。人がいる間は `POLL_INTERVAL`（既定値 30s）ごとに `players` を確認します。0 人になったら **さらに `EMPTY_CONFIRM_SECONDS`（既定値 10s）待って再確認**し、2 回とも 0 人の場合にゲーム内告知 → `save` → `quit` を実行します。タイムアウト（`RESTART_TIMEOUT` 既定値 7200s）時はキャンセルするだけで強制終了はしません。 | B | ephemeral（実行者のみ） | 不要 |
| `/restart cancel` | なし | キューをキャンセルします。B はご自身のもののみ、A はどなたのものでもキャンセルできます。 | B（所有者でも判定します） | ephemeral（実行者のみ） | 不要 |
| `/restart status` | なし | キュー状態や再起動猶予の残り時間を表示します。公開メッセージですので、どなたでも確認できます。 | B | 公開 | 不要 |
| `/restart now` | なし | 待たずに告知 → `save` → `quit` を即時実行します。キューが存在する場合は先にキャンセルします。 | A | ephemeral（実行者のみ） | **要**（Confirm/Cancel、30秒、実行者のみ押せます） |

**再起動時のゲーム内告知について：** `queue` はキュー作成時に 1 回（`game_locales` ごとに 1 行）、`save`/`quit` 直前にもう 1 回告知します。`now` は直前の 1 回のみです。タイムアウトやユーザーによるキャンセルでは告知しません。キュー中に数分おきの定期告知を行うこともありません。

**RestartingWindow について：** `save`/`quit` 送信後、`RestartingWindow`（`RESTART_GRACE` 既定値 360s ≒ このホストの PZ コールドスタート約 6 分）に入ります。ウィンドウ中は `/restart status` 以外のすべてのコマンドが「再起動中、残り N 秒」で拒否され、応答しない RCON を叩き続けることはありません。ウィンドウ終了後も RCON が応答しない場合は通常の失敗として扱われます。

### 2.2 基本運用

| コマンド | 引数 | 説明 | 既定の最低 Tier | 公開範囲 | 要確認 |
|---|---|---|---|---|---|
| `/announce` | `message`: 文字列（必須） | 入力した文字をそのまま `game_locales` ごとに `servermsg` で送信します。翻訳は行いません。長い行は `servermsg_max_chars`（既定値 200）で分割されます。 | A | ephemeral（実行者のみ） | 不要 |
| `/save` | なし | 再起動せずにセーブだけを行います。 | A | ephemeral（実行者のみ） | 不要 |

### 2.3 セッション（キック / BAN / ホワイトリスト / 権限）

| コマンド | 引数 | 説明 | 既定の最低 Tier | 公開範囲 | 要確認 |
|---|---|---|---|---|---|
| `/kick` | `player`: キャラ名（必須、補完あり）<br>`reason`: 理由（任意） | オンラインのプレイヤーをキックします。RCON `kickuser` に対応します。 | A | ephemeral（実行者のみ） | **要** |
| `/ban user` | `player`: キャラ名（必須） | キャラ名で BAN します。`banuser` に対応します。 | A | ephemeral（実行者のみ） | **要** |
| `/ban steamid` | `steamid`: SteamID 文字列（必須） | SteamID で BAN します。`banid` に対応します。オフラインでも BAN できます。 | A | ephemeral（実行者のみ） | **要** |
| `/unban user` | `player`: キャラ名（必須） | キャラ名で BAN を解除します。`unbanuser` に対応します。 | A | ephemeral（実行者のみ） | **要** |
| `/unban steamid` | `steamid`: 文字列（必須） | SteamID で BAN を解除します。`unbanid` に対応します。 | A | ephemeral（実行者のみ） | **要** |
| `/whitelist add` | `player`: アカウント名（必須）<br>`password`: パスワード（必須） | ホワイトリストに追加します。`adduser` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/whitelist remove` | `player`: アカウント名（必須） | ホワイトリストから削除します。`removeuserfromwhitelist` に対応します。 | A | ephemeral（実行者のみ） | **要** |
| `/access set` | `player`: キャラ名（必須、補完あり）<br>`level`: 選択（必須：`none` / `observer` / `gm` / `overseer` / `moderator` / `admin`） | ゲーム内の権限を変更します。`setaccesslevel` に対応します。**Break-glass：** 対象がすでに `admin` の場合は `break_glass_user_ids` に登録された Discord ユーザーのみが変更できます。リストが空の場合は既存 admin の変更は禁止されます（非 admin の昇格は可能です）。 | A（+ break-glass） | ephemeral（実行者のみ） | **要** |

### 2.4 テレポート、付与、ホード、プレイヤー状態

| コマンド | 引数 | 説明 | 既定の最低 Tier | 公開範囲 | 要確認 |
|---|---|---|---|---|---|
| `/teleport to-player` | `player`: 移動させる人（必須）<br>`target`: 移動先の人（必須） | `player` を `target` の元へテレポートします。`teleport` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/teleport to-coords` | `player`: キャラ名（必須）<br>`x` / `y` / `z`: 整数（必須） | 座標へテレポートします。`teleportto` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/give item` | `player`: キャラ名（必須）<br>`item`: スクリプト名 例 `Base.Axe`（必須）<br>`count`: 個数（任意、既定値 1、`limits.yaml` で制限します） | アイテムを付与します。`additem` に対応します。スクリプト名が誤っている場合は RCON の原文が返ります。 | A | ephemeral（実行者のみ） | 不要 |
| `/give xp` | `player`: キャラ名（必須）<br>`perk`: Perk 名 例 `Woodwork`（必須）<br>`amount`: 経験値（必須、制限あり） | Perk の経験値を付与します。`addxp` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/give vehicle` | `player`: キャラ名（必須）<br>`script`: 車両スクリプト（必須） | プレイヤーの近くに車両をスポーンします。`addvehicle` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/horde` | `player`: キャラ名（必須）<br>`count`: 数（必須、制限あり） | プレイヤーの近くにホードをスポーンします。`createhorde` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/player god` | `player`: キャラ名（必須） | ゴッドモードを切り替えます。`godmode` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/player invisible` | `player`: キャラ名（必須） | 透明化を切り替えます。`invisible` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/player noclip` | `player`: キャラ名（必須） | ノークリップを切り替えます。`noclip` に対応します。 | A | ephemeral（実行者のみ） | 不要 |

> 個数上限は `config/limits.yaml` でホットリロードされます：`item 1–50`、`xp 1–100000`、`horde 1–50`、`vehicle` は常に 1 です。範囲外の値は拒否され、丸めて実行されることはありません。

### 2.5 天候とイベント

| コマンド | 引数 | 説明 | 既定の最低 Tier | 公開範囲 | 要確認 |
|---|---|---|---|---|---|
| `/weather start-rain` | なし | 雨を開始します。`startrain` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/weather stop-rain` | なし | 雨を止めます。`stoprain` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/weather thunder` | なし | 雷を発生させます。`thunder` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/weather chopper` | なし | ヘリイベントを発生させます。`chopper` に対応します。 | A | ephemeral（実行者のみ） | 不要 |
| `/weather gunshot` | なし | 銃声イベントを発生させます。`gunshot` に対応します。 | A | ephemeral（実行者のみ） | 不要 |

---

## 3. 権限管理

### 3.1 `guild_id` / `role_id` / `user_id` / `channel_id` とは？

- **Guild** は Discord での **サーバー** の呼び方です。設定ファイルの `guild_id` は「ご自身の Discord サーバーの ID」を指します。
- **Role / User / Channel ID** も同様で、Discord の **スノーフレーク ID** と呼ばれる長い数字の文字列（例 `"123456789012345678"`）です。表示名ではなく ID を使用します。
- 名前ではなく ID を使用する理由：ロール名は変更されることがあり、名前で判定するとリネームによって権限が静かに壊れてしまうためです。ID は不変です。

### 3.2 `guild_id` / `role_id` / `user_id` / `channel_id` の取り方

1. Discord で **設定 → 高度な設定 → 開発者モード（Developer Mode）をオン**にしてください。
   - デスクトップ：左下の歯車 → 高度な設定。
   - モバイル：設定 → 高度な設定。
2. サーバーに戻って以下をコピーします：
   - **サーバー ID（`guild_id`）：** サーバーアイコンを右クリック → **ID をコピー**。
   - **ロール ID（`role_id`）：** サーバー設定 → ロール → ロールを右クリック → **ID をコピー**。
   - **ユーザー ID（`user_id`）：** メンバーを右クリック → **ID をコピー**。
   - **チャンネル ID（`channel_id`）：** チャンネルを右クリック → **ID をコピー**。
3. コピーした数字を **引用符で囲んで** `config/permissions.yaml` に貼り付けてください。引用符がないと YAML が大きな数を浮動小数点として解釈してしまいます。

### 3.3 3 つの Tier

| Tier | フィールド | 想定する役割 | 既定で使えるもの |
|---|---|---|---|
| **A** | `admin_role_ids` | オーナー / モデレーター | すべてのコマンドをご利用いただけます。他の方の `/restart queue` もキャンセルできます。`/restart now` も実行できます |
| **B** | `member_role_ids` | 一般 PZ プレイヤー / `@pz` ロール | `/players` + `/restart queue` + `/restart status` をご利用いただけます。ご自身のキューのみキャンセルできます |
| **C** | それ以外 | その他の全員 / `@everyone` | `/players` のみご利用いただけます |

- A と B の両方をお持ちの方は**上位（A）が優先されます**。
- 既定値は `bot/constants.py` の `DEFAULT_MIN_TIER` で定義されています。`command_min_tier` で特定のコマンドだけ B/C に下げることができます（コードの変更は不要です）。

### 3.4 `config/permissions.yaml` サンプル（コピーして編集してください）

```yaml
# ここに記載されたサーバーにだけスラッシュコマンドが同期されます。追加後は Bot を再起動してください（6.1 を参照）。
guilds:
  # ご自身の Discord サーバー ID（サーバーアイコンを右クリック → ID をコピー）
  "123456789012345678":
    # Tier-A：オーナー / モデレーター。信頼できる 1–2 ロールに絞ってください
    admin_role_ids:
      - "111111111111111111"   # @Admin
      - "222222222222222222"   # @Moderator（共同管理者にも権限を与える場合）

    # Tier-B：一般 PZ プレイヤー。このロールをお持ちの方が再起動をキューできます
    member_role_ids:
      - "333333333333333333"   # @pz / @Survivor

    # （任意）これらのチャンネルでのみコマンドを許可します。空の場合はこのサーバーのどこでも使用できます
    command_channel_ids: []
    # 例：#pz-ops だけで許可する場合
    # command_channel_ids:
    #   - "444444444444444444"

    # （任意）Break-glass：すでにゲーム内で admin の方を操作できる Discord ユーザー ID
    # 空の場合は既存 admin の変更は禁止されます（非 admin の昇格は可能です）
    break_glass_user_ids:
      - "555555555555555555"   # オーナーの Discord ユーザー ID

    # （任意）コマンドごとの最低 Tier 上書き。キーは下の許可リストのみ使用できます
    command_min_tier:
      # Tier-B にも告知を許可する場合
      # announce: B
      # ステータスを全員に見せる場合（既定値は B）
      # restart_status: C

    # 許可される上書きキー（誤ったキーは起動時に失敗します）：
    # players, restart_queue, restart_cancel, restart_status, restart_now,
    # announce, save, kick, ban, unban, whitelist, access,
    # teleport, give, horde, player, weather
```

**フィールド補足：**

- `admin_role_ids` / `member_role_ids`：ロール ID の文字列配列です。ここでのタイプミスが「権限不足」の最多原因です。
- `command_channel_ids`：チャンネル ID の配列です。空の場合は制限なしとなります。指定した場合はそれ以外のチャンネルでは「許可されたチャンネルで実行してください」と返信します。
- `break_glass_user_ids`：ユーザー ID の配列です。`/access set` の break-glass 保護に使用します（[2.3](#23-セッションキック--ban--ホワイトリスト--権限)を参照）。
- `command_min_tier`：コマンド key から `A` / `B` / `C` へのマップです（大文字小文字は区別しません）。

### 3.5 ホットリロードとサーバー追加

- **ロール / `command_min_tier` / `command_channel_ids` / `break_glass_user_ids` の変更：** `config/permissions.yaml` を編集すると**次のコマンドから反映**されます（ファイルの `mtime` でホットリロードされます。壊れたファイルは last-good を保持してエラーをログ出力します）。
- **サーバーの追加・削除（`guilds` のキー変更）：** スラッシュ登録は**起動時**に `guilds` の各キーへ `sync` されます。追加後は以下を実行してください：

  ```bash
  docker compose -f compose.bot.yaml restart pz-bot
  # 非 Docker の場合: systemctl restart pz-discord-bot
  ```

- `guilds` に記載されていないサーバーではコマンドは表示されず、DM でも使用できません。

---

## 4. 設定ファイル

| ファイル | 役割 | ホットリロード | 壊した場合 |
|---|---|---|---|
| `config/permissions.yaml` | 権限とチャンネル許可（上記を参照） | あり（ロール/チャンネル/上書きは即時反映されます。新 guild は再起動が必要です） | 起動に失敗するか、実行時は last-good を保持します |
| `config/i18n.yaml` | 表示する言語 | あり | 起動に失敗します |
| `config/limits.yaml` | 数値上限など | あり | 起動に失敗します |
| `config/locales/zh.yaml` `en.yaml` `jp.yaml` | メッセージ束 | あり | 起動に失敗します |

### 4.1 `config/i18n.yaml`

```yaml
# Discord の Embed で言語ごとに 1 フィールド表示します
discord_locales:
  - zh
  - en
  - jp
# ゲーム内は言語ごとに servermsg を連続送信します
game_locales:
  - zh
  - en
  - jp
```

- スラッシュコマンド名とオプション名は常に英語です（Discord の仕様による制限です）。
- 呼び出し元の Discord クライアント言語によって自動的に切り替わることはありません。このファイルの設定に従います。
- 対応言語は `zh`・`en`・`jp` で、並び順が表示順となります。

### 4.2 `config/limits.yaml`

```yaml
item_count:
  min: 1
  max: 50
xp:
  min: 1
  max: 100000
vehicle: 1          # 常に 1 です
horde:
  min: 1
  max: 50
servermsg_max_chars: 200   # servermsg 1 行の最大文字数です（長い行は分割されます）
confirm_timeout_seconds: 30
```

---

## 5. 環境変数

> `.env.example` を `.env` にコピーして記入してください。`.env` は git にコミットしないでください。

| 変数 | 必須 | 既定値 | 備考 |
|---|---|---|---|
| `DISCORD_TOKEN` | **はい** | — | Bot トークンです（1.2 を参照） |
| `RCON_HOST` | **はい** | — | RCON ホストです。記入内容はトポロジによって異なります。[第 6 章の表](#6-デプロイ)をご覧ください。**既定値はありませんので、必ずご記入ください。** |
| `RCON_PORT` | **はい** | — | RCON ポートです（PZ 既定値は 27015 です。`servertest.ini` の `RCONPort` に合わせてください） |
| `RCON_PASSWORD` | **はい** | — | RCON パスワードです（`RCONPassword`） |
| `BOT_NETWORK` | [compose.bot.yaml](compose.bot.yaml) **のみ必須** | — | すでに PZ コンテナが参加している **external** Docker ネットワーク名です。Python プロセスは読みません。別ホスト / ネイティブ構成では空欄で構いません |
| `POLL_INTERVAL` | いいえ | `30` | キュー中に `players` を何秒ごとに確認するかです |
| `RESTART_TIMEOUT` | いいえ | `7200` | キューのタイムアウト秒数です。超えた場合はキャンセルするだけで `quit` はしません |
| `RESTART_GRACE` | いいえ | `360` | `save`+`quit` 後の猶予秒数です（このホストの PZ コールドスタート ≒ 6 分です） |
| `RCON_FAIL_THRESHOLD` | いいえ | `3` | キュー中に RCON が何回連続で失敗したらキャンセルするかです |
| `EMPTY_CONFIRM_SECONDS` | いいえ | `10` | 無人再確認の間隔（秒）です |
| `RCON_TIMEOUT` | いいえ | `10` | RCON 1 回あたりのタイムアウト秒数です |
| `CONFIG_DIR` | いいえ | `config`（コンテナ内 `/app/config`） | 設定ディレクトリです |
| `HEALTH_STATE_PATH` | いいえ | `/tmp/pz-bot-health.json` | ヘルス状態ファイルです（「計画的な再起動」と「本当の障害」を区別します） |
| `LOG_LEVEL` | いいえ | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` から選択できます |

---

## 6. デプロイ

このリポジトリで提供するのは **Bot のみ**です。ゲームサーバーはどこかですでに稼働していることが前提です（Docker コンテナでも、素のプロセスでも構いません）。compose ファイルはトポロジごとに 3 つあります。**同時に起動するのは 1 つだけ**にしてください。サービス名はいずれも `pz-bot`、イメージはいずれも `pz-discord-bot:latest` です。

| 構成 | 使うファイル | `RCON_HOST` に書くもの | `BOT_NETWORK` |
|---|---|---|---|
| PZ が Docker コンテナで、Bot と**同一ホスト** | [compose.bot.yaml](compose.bot.yaml) | PZ の compose **サービス名**（例 `pz-server`） | **必要** |
| PZ が Docker コンテナで、**別マシン** | [compose.bot.remote.yaml](compose.bot.remote.yaml) | そのマシンの **LAN IP**（例 `10.0.0.5`） | 不要 |
| PZ が **Docker 外**（素のプロセス / systemd） | [compose.bot.native.yaml](compose.bot.native.yaml) | 同一ホストは `host.docker.internal`。別ホストは LAN IP | 不要 |

3 ファイルに共通する内容です（すでに書いてありますので、追加で記述する必要はありません）：

- `pz-bot` 1 サービスのみです。ゲームサーバーは起動しません。
- `restart: unless-stopped` です。
- `volumes: ./config:/app/config` — YAML 変更時に rebuild は不要です。
- `logging: json-file, max-size 10m, max-file 5` です。
- `healthcheck: python -m bot.health` — RCON が応答するか、計画的な再起動ウィンドウ内であれば healthy となります。`unhealthy` でもコンテナは停止しません。`start_period` は `RESTART_GRACE`（360s）に合わせています。
- **`docker.sock` はマウントしません**。Bot 側も **RCON ポートをホストに公開しません**。

再起動の仕組みは変わりません。Bot が送るのは `servermsg` → `save` → `quit` だけです。プロセスを立ち上げ直すのはゲームサーバー側の仕事です（コンテナの `restart: unless-stopped`、または素のプロセスに付けた systemd / ウォッチドッグ）。

日常操作は、選んだファイル名に差し替えてください：

```bash
docker compose -f compose.bot.yaml restart pz-bot   # guild 一覧を変えたあとは必須です
docker compose -f compose.bot.yaml down
docker compose -f compose.bot.yaml logs -f pz-bot
docker inspect --format='{{json .State.Health}}' pz-discord-bot-pz-bot-1 | python -m json.tool
```

---

### 6.1 同一ホスト：PZ が Docker 内（`compose.bot.yaml`）

> いちばん多く、いちばん安全な構成です。Bot は既存の PZ ネットワークに参加します。RCON は Docker 内部 DNS の中だけを通ります。**RCON ポートをホストや公開インターネットに晒さないでください。**

**Step 1 — PZ のネットワーク名を確認します**

```bash
docker network ls
# pz_default、pz-server_default、または独自の pz-net を探します
docker inspect <pz-server-container> --format '{{json .NetworkSettings.Networks}}' | python -m json.tool
```

ネットワーク名を控え、`.env` の `BOT_NETWORK` に記入してください。

**Step 2 — `.env` と `config/permissions.yaml` を用意します**

```bash
cp .env.example .env
# .env を編集：
#   DISCORD_TOKEN=...
#   RCON_HOST=pz-server          # PZ の compose サービス名です。localhost ではありません
#   RCON_PORT=27015              # servertest.ini の RCONPort に合わせます
#   RCON_PASSWORD=...
#   BOT_NETWORK=pz_default       # Step 1 で確認した名前です
# config/permissions.yaml を編集：000… を実際の guild_id / role ID に置換します
```

`RCON_HOST` には **サービス名** を記入してください（Docker 内部 DNS が解決します）。**`localhost` は書かないでください** — Bot コンテナ自身のループバックになり、隣のコンテナには届きません。

**Step 3 — 起動します**

```bash
docker compose -f compose.bot.yaml up -d --build
docker compose -f compose.bot.yaml logs -f pz-bot
# "synced slash commands" と "bot ready" が表示されれば成功です
```

このファイルは `BOT_NETWORK` を必須にしています。未記入だと compose は起動を拒否します。ネットワークはすでに存在している必要があります（`external: true`）。compose が新規作成することは**ありません**。

---

### 6.2 別ホスト：PZ が別マシンの Docker 内（`compose.bot.remote.yaml`）

> Bot は別ホストの Docker ネットワークに参加できないため、LAN 経由で RCON に接続します。`BOT_NETWORK` は使いません。Python プロセスも読みません。

**PZ 側ホスト**（本リポジトリではありません）では、RCON を **LAN IP にだけ**公開し、`0.0.0.0` にはバインドしないでください：

```yaml
# 既存の pz-server compose の断片です。本リポジトリにはありません
ports:
  - "10.0.0.5:27015:27015"    # ホストLAN:ホストポート:コンテナポート
# "27015:27015" とは書かないでください（0.0.0.0 にバインドされ、公開インターネットに開きます）
```

ファイアウォールは Bot ホストだけを許可します。例：

```bash
# PZ ホスト上で、Bot ホスト 10.0.0.8 だけが 27015 に届くようにします
sudo ufw allow from 10.0.0.8 to any port 27015 proto tcp
```

**Bot を動かすマシン側：**

```bash
cp .env.example .env
# .env を編集：
#   DISCORD_TOKEN=...
#   RCON_HOST=10.0.0.5          # PZ ホストの LAN IP です。サービス名ではなく、可能なら公開 IP も避けます
#   RCON_PORT=27015             # 上で公開したホスト側ポートです
#   RCON_PASSWORD=...
#   BOT_NETWORK は空欄で構いません

docker compose -f compose.bot.remote.yaml up -d --build
docker compose -f compose.bot.remote.yaml logs -f pz-bot
```

このファイルに `networks:` は**なく**、ポート公開も**ありません**。再起動はこれまでどおり PZ コンテナ自身の `restart: unless-stopped` です。この Bot が別マシンのコンテナを `docker restart` することはありませんし、できません。

起動前に Bot ホストから疎通を確認します：

```bash
nc -vz 10.0.0.5 27015
# または：python -c "import socket; s=socket.create_connection(('10.0.0.5',27015),5); print('ok'); s.close()"
```

---

### 6.3 PZ が Docker 外（`compose.bot.native.yaml`）

> PZ は素のプロセスです（公式 dedicated、steamcmd、systemd ユニットなど）。参加できる Docker ネットワークはありません。Bot コンテナはホスト経由で RCON に届く必要があります。

**`RCON_HOST` の書き方：**

| PZ の場所 | `RCON_HOST` |
|---|---|
| Bot と**同一ホスト** | `host.docker.internal`（compose にすでに `extra_hosts: host.docker.internal:host-gateway` があります） |
| **別マシン** | そのマシンの LAN IP（通信経路は 6.2 と同じです） |

**注意点：** コンテナからホストの `127.0.0.1` は見えません。PZ の RCON が `127.0.0.1` だけにバインドされていると、`host.docker.internal` でもつながりません。次のいずれかにしてください：

1. PZ の RCON を `0.0.0.0` か LAN NIC にバインドし、ファイアウォールで Docker ブリッジ / Bot ホストだけを許可してから `host.docker.internal` を使います。
2. **Linux のみ：** [compose.bot.native.yaml](compose.bot.native.yaml) のコメントアウトされた `network_mode: host` を有効にし、`RCON_HOST=127.0.0.1` にして `extra_hosts` を削除します。Windows / macOS の Docker Desktop には本物のホストネットワークがありません。

**Bot を動かすマシン側：**

```bash
cp .env.example .env
# .env を編集：
#   DISCORD_TOKEN=...
#   RCON_HOST=host.docker.internal   # 同一ホストです。PZ が別マシンなら LAN IP にします
#   RCON_PORT=27015
#   RCON_PASSWORD=...
#   BOT_NETWORK は空欄で構いません

docker compose -f compose.bot.native.yaml up -d --build
docker compose -f compose.bot.native.yaml logs -f pz-bot
```

再起動は運用者側の責任です。Bot が送るのはこれまでどおり `servermsg` → `save` → `quit` だけです。素のプロセスには `restart: unless-stopped` がないため、systemd やウォッチドッグで PZ を立ち上げ直さないと、`/restart` のあとゲームサーバーは戻りません。

---

### 6.4 Bot を Docker なしで動かす

> Bot 自身をホストプロセスとして動かします。PZ 側の 3 トポロジすべてで使えます。変わるのは `RCON_HOST` だけです。

**Step 1 — Python を用意します**

```bash
# Python 3.12+ が必要です
python3 --version

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Step 2 — 設定と環境変数を用意します**

```bash
cp .env.example .env
# BOT_NETWORK は不要です（compose.bot.yaml 専用です）
# RCON_HOST：
#   同一ホストの素の PZ / 127.0.0.1 に公開した Docker → 127.0.0.1
#   別マシンの PZ                                       → LAN IP
```

`.env` を使わず直接 `export` していただいても構いません：

```bash
export DISCORD_TOKEN=...
export RCON_HOST=127.0.0.1
export RCON_PORT=27015
export RCON_PASSWORD=...
export CONFIG_DIR=$(pwd)/config
```

**Step 3 — フォアグラウンドで実行します**

```bash
# .env をご利用の場合（手動 export です。python-dotenv は同梱していません）
export $(cat .env | xargs)   # .env に空白や引用符が含まれていなければ使用できます
python -m bot

# またはワンライナーで実行します
DISCORD_TOKEN=... RCON_HOST=127.0.0.1 RCON_PORT=27015 RCON_PASSWORD=... python -m bot
```

`bot ready` が表示されれば成功です。`Ctrl+C` で停止できます。

**Step 4 — systemd で常駐させます（Linux）**

`/etc/systemd/system/pz-discord-bot.service` を作成します：

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

その後、以下を実行してください：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pz-discord-bot
sudo systemctl status pz-discord-bot
sudo journalctl -u pz-discord-bot -f
```

**Docker なしのヘルスチェック：**

```bash
python -m bot.health; echo $?
# 0 = healthy、1 = unhealthy です
```

---

## 7. ローカル開発と実行

### 7.1 セットアップします

```bash
python3 --version   # 3.12+ が必要です
python -m venv .venv
source .venv/bin/activate   # Windows Git Bash: source .venv/Scripts/activate
                            # Windows CMD:      .venv\Scripts\activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` は `pytest` / `pytest-asyncio` を追加でインストールします。

### 7.2 設定と起動（開発）

```bash
cp .env.example .env
# DISCORD_TOKEN / RCON_HOST / RCON_PORT / RCON_PASSWORD を記入してください
# ローカル開発では非 Docker 手順（6.4）で構いません — BOT_NETWORK は不要です
# まずはテスト用 Discord サーバーの guild_id だけを permissions.yaml に入れることをおすすめします

python -m bot
# またはワンライナー：
# DISCORD_TOKEN=... RCON_HOST=... RCON_PORT=... RCON_PASSWORD=... python -m bot
```

- 初回起動時に `synced slash commands` が表示されます（`permissions.yaml` の各 guild へ 1 回ずつ同期されます）。
- スラッシュコマンドは Discord 側で最大 1 時間キャッシュされます。テスト時は Bot を再招待するか、少しお待ちください。

### 7.3 テストを実行します

```bash
pytest -q
# 詳細表示
pytest -v
```

対象：Tier 判定、ホットリロード、i18n 分割、`players` パース、再起動ステートマシン（キュー / 拒否 / タイムアウト / 二重ゼロ確認 / 割り込み / 連続失敗）、ヘルス状態をカバーしています。

### 7.4 ログを確認します

- ローカル：`stdout` の JSON 行（`ts` / `level` / `msg` / `operator` / `rcon_cmd` / `queue_state` など）で確認できます。
- Docker：`docker compose -f compose.bot.yaml logs -f pz-bot` で確認できます（別ホスト / ネイティブ構成ではファイル名を `compose.bot.remote.yaml` / `compose.bot.native.yaml` に差し替えてください）。
- systemd：`journalctl -u pz-discord-bot -f` で確認できます。

---

## 8. よくある質問

**スラッシュコマンドが表示されません。**

- 招待 URL に `applications.commands` が含まれているか確認してください。
- `config/permissions.yaml` にご自身の `guild_id`（サーバーアイコンを右クリック → ID をコピー）が引用符付きで記載されているか確認してください。
- guild 追加後に Bot を再起動しましたか。ログに `synced slash commands` が出力されているか確認してください。
- Discord のキャッシュは最大 1 時間です — 再招待するか、しばらくお待ちください。

**「権限不足」と表示されます。**

- ご自身のアカウントが `admin_role_ids` / `member_role_ids` のロールをお持ちか確認してください（ロールを右クリック → ID をコピーして突き合わせてください）。
- `command_min_tier` でそのコマンドの最低 Tier を上げていないか確認してください。
- `command_channel_ids` で現在のチャンネルが制限されていないか確認してください。

**「サーバー再起動中、残り N 秒」と表示されます。**

- 正常な `RestartingWindow`（既定値 360s）です。`save`/`quit` 直後は `/restart status` 以外がブロックされ、応答しない RCON を叩き続けないようにしています。ウィンドウが終了するまでお待ちください。

**RCON に失敗します。**

- `RCON_HOST` / `RCON_PORT` / `RCON_PASSWORD` が `servertest.ini` の設定と一致しているか確認してください。
- 同一ホスト Docker（`compose.bot.yaml`）：`RCON_HOST` はサービス名（例 `pz-server`）であり `localhost` ではないか、`BOT_NETWORK` は PZ コンテナと同じネットワークか確認してください。
- 別ホスト Docker（`compose.bot.remote.yaml`）：`RCON_HOST` は PZ ホストの LAN IP です。RCON は LAN にだけ公開し、ファイアウォールは Bot ホストだけを許可してください。
- ネイティブ PZ（`compose.bot.native.yaml`）：同一ホストなら `host.docker.internal` です。`127.0.0.1` は Bot コンテナ自身を指すので使わないでください。別ホストなら LAN IP です。
- Bot が Docker 外：ファイアウォールで RCON ポートが許可されているか、RCON は内部アドレスか `127.0.0.1` にバインドされており公開されていないか確認してください。
- ログの `rcon_cmd` と `detail` フィールドを確認してください。

**`permissions.yaml` を修正しても反映されません。**

- ロール / チャンネル / Tier 上書き：次のコマンド実行時に反映されます（ホットリロードされます）。
- サーバーの追加・削除（`guilds` のキー変更）：Bot の再起動が必要です。

**`permissions.yaml` 編集後に起動しません。**

- YAML 構文エラーや `command_min_tier` の誤ったキーで起動に失敗します。実行時の誤編集は last-good を保持して `error` をログ出力しますので、権限が静かに「全員 C」や「全員 A」になることはありません。

---

## 9. ディレクトリ構成

```
.
├── bot/                 # Python パッケージ（discord.py + RCON + キュー + 権限 + i18n）
│   ├── app.py           # Bot 生成、Cog 登録、guild ごとのスラッシュ同期を行います
│   ├── settings.py      # 環境変数を管理します
│   ├── config.py        # YAML 読み込みと mtime ホットリロードを行います
│   ├── permissions.py   # 3 Tier とチャンネル / break-glass 判定を行います
│   ├── rcon_client.py   # async Source RCON ラッパーと players パースを行います
│   ├── restart_queue.py # グローバル RestartQueue ステートマシンを管理します
│   ├── discord_util.py  # ゲート、Embed、i18n、確認ボタンを提供します
│   └── cogs/            # スラッシュコマンド群です
├── config/
│   ├── permissions.yaml
│   ├── i18n.yaml
│   ├── limits.yaml
│   └── locales/{zh,en,jp}.yaml
├── compose.bot.yaml         # 同一ホスト：PZ コンテナ + Bot
├── compose.bot.remote.yaml  # 別ホスト：PZ コンテナが別マシン
├── compose.bot.native.yaml  # PZ が Docker 外
├── Dockerfile
├── requirements.txt / requirements-dev.txt
└── tests/               # pytest です
```

用語集は [CONTEXT.md](CONTEXT.md) をご覧ください。コードとコメントは英語で記述されています。
