#!/usr/bin/env python3
"""
プロフィールREADMEを動的に更新するスクリプト。

README.md 内の各マーカー区間を、生成したコンテンツで差し替える:

    <!-- ACTIVITY:START -->  ...  <!-- ACTIVITY:END -->   最近の公開アクティビティ
    <!-- TIP:START -->       ...  <!-- TIP:END -->        日替わりの開発Tips
    <!-- CLOCK:START -->     ...  <!-- CLOCK:END -->      現在時刻(JST)と稼働時間帯

依存は標準ライブラリのみ。認証は Actions が渡す GITHUB_TOKEN を使う(公開データのみ)。
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = os.environ.get("GH_USERNAME", "").strip()
TOKEN = os.environ.get("GH_TOKEN", "").strip()
README = os.environ.get("README_PATH", "README.md")
JST = timezone(timedelta(hours=9))


# --------------------------------------------------------------------------- #
# GitHub API
# --------------------------------------------------------------------------- #
def gh_get(path: str):
    """GitHub API を叩いて JSON を返す。失敗時は None。"""
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", f"{USERNAME}-profile-bot")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"[warn] API {path} failed: {exc}", file=sys.stderr)
        return None


# --------------------------------------------------------------------------- #
# セクション生成
# --------------------------------------------------------------------------- #
def render_activity() -> str:
    """直近の公開イベントを人間可読な行に変換する。"""
    events = gh_get(f"/users/{USERNAME}/events/public") or []
    lines: list[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        # 同一内容の連続イベントを1行に圧縮する
        if line not in seen:
            seen.add(line)
            lines.append(line)

    for ev in events:
        if len(lines) >= 5:
            break
        etype = ev.get("type")
        repo = ev.get("repo", {}).get("name", "?")
        repo_md = f"[`{repo}`](https://github.com/{repo})"
        payload = ev.get("payload", {})

        if etype == "PushEvent":
            n = payload.get("size") or len(payload.get("commits", [])) or 1
            add(f"🟢 **{n} commit{'s' if n != 1 else ''}** を {repo_md} に push")
        elif etype == "PullRequestEvent":
            act = payload.get("action", "updated")
            num = payload.get("number", "")
            add(f"🔀 PR #{num} を **{act}** — {repo_md}")
        elif etype == "IssuesEvent":
            act = payload.get("action", "updated")
            num = payload.get("issue", {}).get("number", "")
            add(f"📋 Issue #{num} を **{act}** — {repo_md}")
        elif etype == "CreateEvent":
            ref = payload.get("ref_type", "branch")
            add(f"✨ 新しい {ref} を {repo_md} に作成")
        elif etype == "WatchEvent":
            add(f"⭐ {repo_md} に Star")
        elif etype == "ForkEvent":
            add(f"🍴 {repo_md} を Fork")
        elif etype == "ReleaseEvent":
            tag = payload.get("release", {}).get("tag_name", "")
            add(f"🚀 Release **{tag}** — {repo_md}")

    if not lines:
        add("_最近の公開アクティビティはまだありません_ 🌱")

    return "\n".join(f"- {l}" for l in lines)


# 日替わりで巡回する開発Tips。日付シードで決定的に選ぶ(毎日同じ値=差分が安定)。
TIPS = [
    "`git commit --amend --no-edit` で直前のコミットに変更をそっと追記できる。",
    "`git switch -c feat/x` は `checkout -b` の現代的な別名。意図が読みやすい。",
    "`git bisect` は二分探索でバグ混入コミットを自動特定してくれる。",
    "`rg`(ripgrep) は `grep -r` より桁違いに速く、.gitignore も尊重する。",
    "`jq -c .` で JSON を1行化、`jq .` で整形。ログ整形の定番。",
    "`python -m http.server` で今いるディレクトリを即席Webサーバに。",
    "`curl -w '%{time_total}\\n' -o /dev/null -s URL` でリクエスト時間だけ測れる。",
    "`code --diff a b` で VS Code を差分ビューアとして単発起動できる。",
    "`git log --oneline --graph --all` でブランチの分岐を俯瞰できる。",
    "`set -euo pipefail` を bash スクリプト先頭に置くと失敗を早期検知できる。",
    "`gh pr create --fill` でコミットからPR本文を自動生成。",
    "`tldr <cmd>` は man より実例が早い。`tldr tar` で圧縮コマンドが即わかる。",
]


def render_tip() -> str:
    day_index = datetime.now(JST).toordinal()
    tip = TIPS[day_index % len(TIPS)]
    return f"> 💡 **今日のTips** — {tip}"


def render_stats() -> str:
    """ユーザー情報と全リポを集計し、自前の統計カードを描く(外部SVG非依存)。"""
    user = gh_get(f"/users/{USERNAME}") or {}
    repos = gh_get(f"/users/{USERNAME}/repos?per_page=100&type=owner") or []

    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    forks = sum(r.get("forks_count", 0) for r in own)
    public_repos = user.get("public_repos", len(repos))
    followers = user.get("followers", 0)
    following = user.get("following", 0)

    rows = [
        ("📦 Public repos", public_repos),
        ("⭐ Total stars", stars),
        ("🍴 Total forks", forks),
        ("👥 Followers", followers),
        ("➡️  Following", following),
    ]
    label_w = max(len(label) for label, _ in rows)
    lines = ["```text"]
    for label, val in rows:
        lines.append(f"{label.ljust(label_w)}  {val:>6,}")
    lines.append("```")
    return "\n".join(lines)


def render_langs() -> str:
    """全リポジトリの言語バイト数を合算し、比率バーを描く。"""
    repos = gh_get(f"/users/{USERNAME}/repos?per_page=100&type=owner&sort=pushed") or []
    totals: dict[str, int] = {}

    # レート制限と実行時間のため、最近 push した上位30リポに絞る
    for repo in repos[:30]:
        if repo.get("fork"):
            continue
        full = repo.get("full_name")
        if not full:
            continue
        langs = gh_get(f"/repos/{full}/languages") or {}
        for lang, by in langs.items():
            totals[lang] = totals.get(lang, 0) + int(by)

    if not totals:
        return "_言語データを取得できませんでした_ 🤔"

    grand = sum(totals.values())
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:8]

    bar_width = 22
    lines = ["```text"]
    name_w = max(len(name) for name, _ in top)
    for name, by in top:
        pct = by / grand * 100
        filled = round(pct / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        lines.append(f"{name.ljust(name_w)}  {bar}  {pct:5.1f}%")
    lines.append("```")
    return "\n".join(lines)


def render_clock() -> str:
    now = datetime.now(JST)
    hour = now.hour
    if 5 <= hour < 11:
        mood = "☀️ おはようコーディング"
    elif 11 <= hour < 17:
        mood = "💻 集中タイム"
    elif 17 <= hour < 23:
        mood = "🌆 夕方のハック"
    else:
        mood = "🌙 深夜の実装(ほどほどに)"
    stamp = now.strftime("%Y-%m-%d %H:%M JST")
    return f"🕒 最終更新: **{stamp}** — {mood}"


# --------------------------------------------------------------------------- #
# マーカー差し替え
# --------------------------------------------------------------------------- #
def replace_section(text: str, key: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- {key}:START -->).*?(<!-- {key}:END -->)",
        re.DOTALL,
    )
    replacement = rf"\g<1>\n{body}\n\g<2>"
    new_text, n = pattern.subn(replacement, text)
    if n == 0:
        print(f"[warn] marker {key} not found in {README}", file=sys.stderr)
    return new_text


def main() -> int:
    if not USERNAME:
        print("[error] GH_USERNAME env var is required", file=sys.stderr)
        return 1

    with open(README, encoding="utf-8") as fh:
        text = fh.read()

    text = replace_section(text, "ACTIVITY", render_activity())
    text = replace_section(text, "STATS", render_stats())
    text = replace_section(text, "LANGS", render_langs())
    text = replace_section(text, "TIP", render_tip())
    text = replace_section(text, "CLOCK", render_clock())

    with open(README, "w", encoding="utf-8") as fh:
        fh.write(text)

    print("README updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
