# star-history

GitHub が [2026-06-30 に stargazers API をオーナー/コラボレーター限定に制限](https://github.blog/changelog/2026-06-30-upcoming-access-restrictions-to-public-api-endpoints-and-ui-views/)したため、star-history.com の README 埋め込みチャートが機能しなくなった。このリポジトリはその代替として、自分のリポジトリのスター履歴チャートを GitHub Actions で定期生成し、静的 SVG として配信する。

- 毎日 06:00 JST（cron）にオーナーの fine-grained PAT でスター履歴を取得
- `charts/` にライト/ダークテーマの SVG を生成してコミット
- 各リポジトリの README は `raw.githubusercontent.com` の固定 URL を参照するだけなので、README 側の更新は不要
- 依存ライブラリなし（Python 標準ライブラリのみ）。スターを付けたユーザーの情報は保存せず、日時のみ記録

## チャート

<p>
  <img alt="Star history of ryhara/hand_visibility_detector (light)" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/ryhara_hand_visibility_detector.svg" width="49%">
  <img alt="Star history of ryhara/hand_visibility_detector (dark)" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/ryhara_hand_visibility_detector_dark.svg" width="49%">
</p>

<p>
  <img alt="Star history of ryhara/hamer-mini (light)" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/ryhara_hamer-mini.svg" width="49%">
  <img alt="Star history of ryhara/hamer-mini (dark)" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/ryhara_hamer-mini_dark.svg" width="49%">
</p>

## 使い方

### 1. トークンを登録する

fine-grained PAT（対象リポジトリに対して **Metadata: Read-only** があれば十分）を、このリポジトリの Secret `STAR_HISTORY_TOKEN` に登録する:

```bash
gh secret set STAR_HISTORY_TOKEN -R ryhara/star-history
```

### 2. 対象リポジトリを追加する

`repos.txt` に 1 行 1 リポジトリで書く。push すると即座にチャートが再生成される。

### 3. README に埋め込む

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ryhara/star-history/main/charts/{owner}_{repo}_dark.svg">
  <img alt="Star History" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/{owner}_{repo}.svg">
</picture>
```

### 手動実行・ローカル実行

```bash
gh workflow run update.yml -R ryhara/star-history   # 手動トリガー
GH_TOKEN=$(gh auth token) python3 generate_star_history.py  # ローカル
```

## 注意

- スター **数** の推移のみを公開する。誰がスターしたか（GitHub が制限したデータ）は保存・公開しない
- fine-grained PAT には有効期限があるため、失効したら Secret を更新する
- リポジトリが 60 日間無活動だと scheduled workflow は自動停止する（このリポジトリはチャート更新コミットで活動が続くため実質問題にならない）
