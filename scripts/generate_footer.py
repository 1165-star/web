#!/usr/bin/env python3
"""全ページ共通のフッターを生成・更新する。

使い方: リポジトリのルートで `python3 scripts/generate_footer.py`

- 404.html と Search Console 確認用 google*.html を除く全 .html が対象。
- 既存の <footer> を取り除き、</main> の直後に共通フッターを入れる(マーカーで囲むので何度実行しても同じ結果)。
- <head> に assets/footer.css を読み込む。
- html の lang が ja 以外のページは、ラベルを英語にする。
- アプリを追加したときは下の APPS に1行足して、このスクリプトを実行する。
"""
import os, re, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEAR = datetime.date.today().year
START, END = "<!-- tya-footer:start -->", "<!-- tya-footer:end -->"

# (フォルダ名, アプリ名)  ※並びはトップページの掲載順
APPS = [
    ("app-report-card", "アプリ成績表"),
    ("blood-pressure-history", "血圧メモ"),
    ("houkaku-compass", "ゆびさすコンパス"),
    ("memonowa", "めものわ"),
    ("monosashi", "モノサシ"),
    ("pet-health-management", "ぺっときろく"),
    ("scroll-capture", "縦長スクショ"),
    ("shrink", "Shrink"),
    ("sutamina-techo", "スタミナ手帳"),
]
APP_NAME = dict(APPS)
L = {
    "ja": dict(sub="スマホアプリ開発", apps="アプリ一覧", site="サイト", top="ちゃ開発組トップ",
               sitepp="サイトのプライバシーポリシー", intro="アプリ紹介", manual="取扱説明書",
               notes="リリースノート", pp="プライバシーポリシー", nav_apps="アプリ一覧", nav_app="このアプリ", this="のページ"),
    "en": dict(sub="Smartphone app development", apps="Apps", site="Site", top="Cha Kaihatsu-gumi Home",
               sitepp="Site Privacy Policy", intro="About the app", manual="User Guide (Japanese)",
               notes="Release notes", pp="Privacy Policy", nav_apps="Apps", nav_app="This app", this=""),
}


def files():
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "*.html"], capture_output=True, text=True).stdout.split()
    return [f for f in out if f != "404.html" and not os.path.basename(f).startswith("google")]


def build(rel, lang):
    t = L["ja" if lang == "ja" else "en"]
    parts = rel.split("/")
    depth = len(parts) - 1
    up = "../" * depth if depth else "./"
    app = parts[0] if parts[0] in APP_NAME else None
    here = rel
    def a(href, label, target_rel=None):
        cur = ' aria-current="page"' if target_rel == here else ""
        return f'<li><a href="{href}"{cur}>{label}</a></li>'
    cols = []
    if app:
        base = up + app + "/"
        # 同じ階層のページから見た相対パス
        def rp(p): return base + p
        items = [
            a(rp("index.html") if False else rp(""), t["intro"], f"{app}/index.html"),
            a(rp("manual/"), t["manual"], f"{app}/manual/index.html"),
            a(rp("release-notes.html"), t["notes"], f"{app}/release-notes.html"),
            a(rp("privacy-policy.html"), t["pp"], f"{app}/privacy-policy.html"),
        ]
        cols.append(f'<div class="tf-col"><h2>{APP_NAME[app]}</h2><ul>{"".join(items)}</ul></div>')
    apps = "".join(a(f"{up}{d}/", n, f"{d}/index.html") for d, n in APPS)
    cols.append(f'<div class="tf-col tf-col-apps"><h2>{t["apps"]}</h2><ul>{apps}</ul></div>')
    site = a(up if depth else "./", t["top"], "index.html") + a(up + "privacy-policy.html", t["sitepp"], "privacy-policy.html")
    cols.append(f'<div class="tf-col"><h2>{t["site"]}</h2><ul>{site}</ul></div>')
    return (
        f'{START}\n<footer class="tya-footer">\n<div class="tf-inner">\n'
        f'<div class="tf-brand"><img src="{up}assets/profile.jpg" alt="" width="44" height="44">'
        f'<div><a class="tf-brand-name" href="{up if depth else "./"}">ちゃ開発組</a><span class="tf-brand-sub">{t["sub"]}</span></div></div>\n'
        f'<nav class="tf-cols" aria-label="{t["nav_apps"]}">\n' + "\n".join(cols) + '\n</nav>\n'
        f'<p class="tf-copy">&copy; <span id="year">{YEAR}</span> ちゃ開発組</p>\n</div>\n</footer>\n{END}'
    )


changed = 0
for rel in files():
    p = os.path.join(ROOT, rel)
    s = open(p, encoding="utf-8").read()
    lang = (re.search(r'<html[^>]*\blang="([^"]*)"', s) or [None, "ja"])[1]
    new = s
    new = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", new, flags=re.S)
    new = re.sub(r"[ \t]*<footer\b.*?</footer>\n?", "", new, flags=re.S)
    if "</main>" not in new:
        print("skip (no </main>):", rel); continue
    new = new.replace("</main>", "</main>\n" + build(rel, lang), 1)
    depth = rel.count("/")
    css = f'<link rel="stylesheet" href="{"../" * depth if depth else "./"}assets/footer.css">\n'
    new = re.sub(r'<link rel="stylesheet" href="[^"]*assets/footer\.css">\n?', "", new)
    new = new.replace("</head>", css + "</head>", 1)
    if new != s:
        open(p, "w", encoding="utf-8").write(new); changed += 1
print("updated", changed, "files")
