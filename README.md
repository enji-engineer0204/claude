# Instagram Follow / Follower Tracker

一定間隔で Instagram アカウントの **フォロー（following）/ フォロワー（followers）一覧** を記録し、
前回スナップショットとの **差分** を計算します。

- 前回と同じ → **通知しない**
- 差分あり → 内容（誰が増えた/減ったか）を **Discord / Slack に通知**

追跡できる差分（設定で選択可）:

| キー | 意味 |
| --- | --- |
| `new_following`  | 新規フォロー（フォロー中の増加） |
| `lost_following` | フォロー解除（フォロー中の減少） |
| `new_followers`  | 新規フォロワー |
| `lost_followers` | フォロワー減（外れた） |

---

## ⚠️ 重要な前提（必ず読んでください）

- このツールは **対象アカウント本人の同意がある場合にのみ** 使ってください。
  他人のアカウントを本人に無断で監視する目的では使わないでください。
- Instagram の公式 API ではフォロー/フォロワー **一覧** は取得できません。
  本ツールは「本人がブラウザでログイン済みのセッション（`sessionid` クッキー）」を
  再利用して取得します。これは Instagram の利用規約上グレー〜違反にあたり、
  **アクセス頻度が高いとアカウント制限・一時ブロックの恐れ** があります。
  取得間隔は **6〜24 時間に 1 回程度** を推奨します（本ツールの既定は手動 / 控えめ）。
- `sessionid` は **パスワード相当の機密情報** です。Git にコミットしないでください
  （`config.json` と `.env` は `.gitignore` 済み）。

---

## セットアップ

```bash
pip install -r requirements.txt
cp config.example.json config.json
```

### sessionid を Chrome から取得する

対象アカウント本人が Chrome で Instagram にログインした状態で:

1. `instagram.com` を開く
2. `F12`（デベロッパーツール）→ **Application** タブ
3. 左メニュー **Storage → Cookies → https://www.instagram.com**
4. `sessionid` の **Value** をコピー

この値を `config.json` の `session_id`、または環境変数 `INSTAGRAM_SESSIONID` に設定します。
（環境変数のほうがファイルに平文で残らず安全です。）

### config.json の例

```json
{
  "session_id": "",
  "target_username": "",
  "track": ["new_following", "lost_following", "new_followers", "lost_followers"],
  "notifier": { "type": "discord", "webhook_url": "" },
  "data_dir": "data",
  "max_amount": 0
}
```

- `session_id`: Chrome から取得した sessionid（空なら環境変数 `INSTAGRAM_SESSIONID` を使用）
- `target_username`: 追跡対象のユーザー名。**空ならログイン中の本人アカウント** を対象にします
- `track`: 通知したい差分の種類（上の表のキー）
- `notifier.type`: `discord` / `slack` / `none`
- `notifier.webhook_url`: Webhook URL（環境変数 `WEBHOOK_URL` でも可）
- `max_amount`: 一度に取得する最大件数。`0` で全件（大きいアカウントほど制限リスク↑）

---

## 実行

一回だけチェック:

```bash
python -m tracker run
```

通知を送らずに差分だけ確認（テスト）:

```bash
python -m tracker run --dry-run
```

一定間隔で常駐（既定 6 時間）:

```bash
python -m tracker run --loop --interval 6h
```

### cron で自動実行（PC 常駐 / サーバー向け）

例: 6 時間ごと

```cron
0 */6 * * * cd /path/to/this/repo && /usr/bin/python3 -m tracker run >> data/cron.log 2>&1
```

---

## 仕組み

1. `sessionid` で instagrapi にログイン（デバイス情報は `data/ig_settings.json` にキャッシュ）
2. 対象アカウントの followers / following を取得
3. `data/snapshot.json`（前回）と比較して差分を計算
4. 差分があれば notifier で通知。なければ何もしない
5. 今回の結果を新しいスナップショットとして保存

初回はスナップショットが無いため **ベースライン作成のみ・通知なし** です。
