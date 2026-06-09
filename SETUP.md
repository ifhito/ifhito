# 動的プロフィールREADME セットアップ手順

## 1. ユーザー名を置換
`__USERNAME__` を自分のGitHubユーザー名に一括置換する（macOS）:

```bash
cd ~/Documents/github-profile-readme
grep -rl __USERNAME__ . | xargs sed -i '' 's/__USERNAME__/あなたのユーザー名/g'
```

## 2. 「自分専用リポジトリ」を作る
GitHubで **リポジトリ名を自分のユーザー名と完全一致** させて新規作成する
（例: ユーザー名が `tanaka` なら リポジトリ名も `tanaka`）。これがプロフィールREADMEの条件。
- Public で作成
- README/`.gitignore`/license は **追加しない**（空で作る）

## 3. push する
```bash
cd ~/Documents/github-profile-readme
git init -b main
git add .
git commit -m "feat: dynamic profile README"
git remote add origin git@github.com:あなたのユーザー名/あなたのユーザー名.git
git push -u origin main
```

## 4. Actionsを動かす
1. リポジトリの **Settings → Actions → General → Workflow permissions** を
   **「Read and write permissions」** に変更（READMEへの自動コミットに必要）。
2. **Actions タブ → "Update profile README" → Run workflow** で手動実行 → 数十秒で
   「最近のアクティビティ」「今日のTips」「最終更新時刻」が埋まる。
3. 以降は6時間ごとに自動更新される。

## 仕組み
- `scripts/update_readme.py` が `<!-- KEY:START -->`〜`<!-- KEY:END -->` の区間だけを差し替える
- 認証は Actions が自動付与する `GITHUB_TOKEN` のみ。外部トークン不要
- 依存は Python標準ライブラリのみ

## 拡張アイデア
- **Spotify**: 最近聴いた曲セクション → `SPOTIFY:START/END` マーカーを追加し、
  Spotify API のトークンを Secrets に入れて `gh_get` 同様の関数を足す
- **WakaTime**: コーディング時間の内訳
- **ブログRSS**: 最新記事リストを `feedparser` 無しでも `xml.etree` で取得可能
- **草アート / Snake**: 別ワークフロー `Platane/snk` を足すと貢献グラフを蛇が食べるSVGを生成
