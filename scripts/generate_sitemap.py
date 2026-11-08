#!/usr/bin/env python3
"""sitemap.xml を自動生成する。

使い方: リポジトリのルートで `python3 scripts/generate_sitemap.py`

- 全 .html を対象にする(404.html と Search Console 確認用 google*.html は除く)。
- noindex のページ、および canonical が自分自身ではないページ(重複ページ)は載せない。
- lastmod は git の最終コミット日。未コミットの変更があるファイルは今日の日付。
"""
import os, re, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://tya-kaihatsu.com"
TODAY = datetime.date.today().isoformat()


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True).stdout.strip()


dirty = set()
for line in git("status", "--porcelain").splitlines():
    dirty.add(line[3:].strip().strip('"'))


def url_of(rel):
    parts = rel.split("/")
    if parts[-1] == "index.html":
        return BASE + "/" + "/".join(parts[:-1]) + ("/" if len(parts) > 1 else "")
    return BASE + "/" + rel


entries = []
for r, _, fs in os.walk(ROOT):
    if ".git" in r.split(os.sep):
        continue
    for f in fs:
        if not f.endswith(".html"):
            continue
        rel = os.path.relpath(os.path.join(r, f), ROOT).replace(os.sep, "/")
        if rel == "404.html" or rel.startswith("google"):
            continue
        src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        if re.search(r'<meta[^>]+name="robots"[^>]+noindex', src, re.I):
            continue
        url = url_of(rel)
        m = re.search(r'<link rel="canonical" href="([^"]+)"', src)
        if m and m.group(1) != url:
            continue  # 重複ページ(別URLがcanonical)は載せない
        last = TODAY if rel in dirty else (git("log", "-1", "--format=%cs", "--", rel) or TODAY)
        entries.append((url, last))

entries.sort(key=lambda e: (e[0].count("/"), e[0]))
out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for url, last in entries:
    out.append(f"  <url><loc>{url}</loc><lastmod>{last}</lastmod></url>")
out.append("</urlset>")
open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"{len(entries)} URLs written to sitemap.xml")
