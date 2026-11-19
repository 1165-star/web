#!/usr/bin/env python3
"""SEO強化の構造化データ・メタ・アプリ情報/FAQセクションを自動生成する(共通仕様46.8)。

使い方: リポジトリのルートで `python3 scripts/generate_seo.py`(何度実行しても結果は同じ)

- 全ページ: robots / author / og:locale / twitter:title・description・image を、無ければ足す。
  取説に無い apple-touch-icon も足す。
- トップ以外の全ページ: BreadcrumbList を作る・更新する。
- アプリ紹介ページ: MobileApplication の拡張項目、description、「アプリ情報」「よくある質問」
  (取説のFAQPageの先頭4問)を作る・更新する。
- トップ: Organization と、カードの全アプリの ItemList(CollectionPage)を作る・更新する。
- 404.html と Search Console 確認用 google*.html は対象外。
"""
import os, re, json, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
BASE = 'https://tya-kaihatsu.com'
FAQ_N = 4
LOCALE = {'ja': 'ja_JP', 'en': 'en_US', 'de': 'de_DE', 'es': 'es_ES', 'fr': 'fr_FR', 'id': 'id_ID',
          'it': 'it_IT', 'ko': 'ko_KR', 'pt': 'pt_BR', 'ru': 'ru_RU', 'zh-Hans': 'zh_CN', 'zh-Hant': 'zh_TW'}
# schema.org の applicationCategory。新しいアプリを足したら追記する(未登録は UtilitiesApplication)
CAT = {'app-report-card': 'DeveloperApplication', 'blood-pressure-history': 'HealthApplication',
       'houkaku-compass': 'UtilitiesApplication', 'memonowa': 'DesignApplication',
       'monosashi': 'LifestyleApplication', 'pet-health-management': 'LifestyleApplication',
       'scroll-capture': 'UtilitiesApplication', 'shrink': 'MultimediaApplication',
       'sutamina-techo': 'UtilitiesApplication'}
CSS = """
    /* アプリ情報・よくある質問(generate_seo.py が差し込む) */
    .app-facts, .app-faq { max-width: 100%; margin: 0 0 36px; text-align: left; }
    .app-facts-heading-wrap, .app-faq-heading-wrap { border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 16px; }
    .app-facts-heading-wrap h2, .app-faq-heading-wrap h2 { margin: 0; padding: 0; border-bottom: none; font-size: 1.15rem; font-weight: 800; text-align: left; }
    .facts-list { display: grid; grid-template-columns: 1fr; gap: 10px; margin: 0; }
    @media (min-width: 768px) { .facts-list { grid-template-columns: repeat(2, 1fr); gap: 14px; } }
    .facts-list > div { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; font-size: 0.86rem; line-height: 1.55; }
    .facts-list dt { margin: 0 0 2px; color: var(--muted); font-size: 0.74rem; font-weight: 700; }
    .facts-list dd { margin: 0; font-weight: 600; }
    .facts-list a { color: var(--accent); text-decoration: none; }
    .facts-list a:hover { text-decoration: underline; }
    .faq-list { display: grid; gap: 10px; }
    .faq-list details { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 0 14px; font-size: 0.88rem; line-height: 1.65; }
    .faq-list summary { cursor: pointer; padding: 12px 0; font-weight: 700; list-style-position: inside; }
    .faq-list details[open] summary { color: var(--accent); }
    .faq-list details p { margin: 0 0 14px; color: var(--fg); }
    .faq-more { margin: 12px 0 0; font-size: 0.86rem; }
    .faq-more a { color: var(--accent); font-weight: 600; text-decoration: none; }
    .faq-more a:hover { text-decoration: underline; }
"""
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
n_changed = 0


def rd(p):
    return open(p, encoding='utf-8', newline='').read()


def wr(p, old, new):
    global n_changed
    if new != old:
        open(p, 'w', encoding='utf-8', newline='').write(new)
        n_changed += 1


def clean(t):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)).strip()


def dumps(o, indent_extra=''):
    t = json.dumps(o, ensure_ascii=False, indent=2)
    return t.replace('\n', '\n' + indent_extra)


def meta(s, name=None, prop=None):
    pat = (r'<meta name="%s" content="([^"]*)"' % name) if name else (r'<meta property="%s" content="([^"]*)"' % prop)
    m = re.search(pat, s)
    return m.group(1) if m else None


def url_of(rel):
    parts = rel.split('/')
    if parts[-1] == 'index.html':
        return BASE + '/' + '/'.join(parts[:-1]) + ('/' if len(parts) > 1 else '')
    return BASE + '/' + rel


def upsert_ld(s, is_match, obj, indent=''):
    """is_match(json) に合う既存のJSON-LDを、内容が違うときだけ置き換える。無ければ最後のJSON-LDの後ろに足す。"""
    last_end = None
    for m in LD_RE.finditer(s):
        last_end = m.end()
        try:
            cur = json.loads(m.group(1))
        except Exception:
            continue
        if is_match(cur):
            if cur == obj:
                return s
            body = '\n' + indent + dumps(obj, indent) + '\n' + (indent[:-2] if indent else '')
            return s[:m.start(1)] + body + s[m.end(1):]
    block = indent + '<script type="application/ld+json">\n' + indent + dumps(obj, indent) + '\n' + indent + '</script>'
    return s[:last_end] + '\n' + block + s[last_end:]


def enhance_meta(rel, s, imgalt=None):
    if 'noindex' in s:
        return s
    lang = re.search(r'<html lang="([^"]+)"', s).group(1)
    add = []
    if 'name="robots"' not in s:
        add.append('<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">')
    if 'name="author"' not in s:
        add.append('<meta name="author" content="ちゃ開発組">')
    if 'og:locale' not in s:
        add.append('<meta property="og:locale" content="%s">' % LOCALE[lang])
    if imgalt and 'og:image:alt' not in s:
        add.append('<meta property="og:image:alt" content="%s">' % html.escape(imgalt, quote=True))
    for k in ('title', 'description'):
        if 'twitter:' + k not in s:
            v = meta(s, prop='og:' + k)
            if v:
                add.append('<meta name="twitter:%s" content="%s">' % (k, v))
    if 'twitter:image"' not in s:
        v = meta(s, prop='og:image')
        if v:
            add.append('<meta name="twitter:image" content="%s">' % v)
    if add:
        m = re.search(r'<meta name="twitter:card"[^>]*>', s)
        s = s[:m.end()] + '\n' + '\n'.join(add) + s[m.end():]
    if 'apple-touch-icon' not in s:
        m = re.search(r'<link rel="icon"[^>]*>', s)
        s = s[:m.end()] + '\n<link rel="apple-touch-icon" href="%sassets/apple-touch-icon.png">' % ('../' * rel.count('/')) + s[m.end():]
    return s


def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


def is_bc(o):
    return isinstance(o, dict) and o.get('@type') == 'BreadcrumbList'


APPS = sorted(d for d in os.listdir('.') if os.path.isfile(d + '/index.html'))
appname = {a: clean(re.search(r'<h1>(.*?)</h1>', rd(a + '/index.html'), re.S).group(1)) for a in APPS}

# ---- アプリ紹介ページ
for a in APPS:
    rel = a + '/index.html'
    s0 = rd(rel)
    s = s0
    name, u = appname[a], url_of(rel)
    lead = clean(re.search(r'class="app-lead-desc">(.*?)</p>', s, re.S).group(1))
    specs = [clean(x) for x in re.findall(r'class="spec-item">(?:<span>[^<]*</span>)?(.*?)</(?:span|div)>', s)]
    specs = [re.sub(r'^[^\w　-鿿]+', '', x) for x in specs]
    pill = clean(re.search(r'class="(?:tag-badge|category-pill)">(.*?)</span>', s, re.S).group(1))
    play = re.search(r'href="(https://play\.google\.com/store/apps/details\?id=[^"]+)"', s)
    has_manual = os.path.exists(a + '/manual/index.html')
    # MobileApplication
    ld = next(json.loads(m.group(1)) for m in LD_RE.finditer(s) if '"MobileApplication"' in m.group(1))
    shots = [BASE + '/' + a + '/' + h[2:] for h in re.findall(r'<a class="gallery-thumb" href="(\./images/store/\d+\.webp)"', s)]
    ld['@id'] = u + '#app'
    ld['applicationCategory'] = CAT.get(a, 'UtilitiesApplication')
    ld['applicationSubCategory'] = pill
    ld['image'] = ([BASE + '/' + a + '/images/store/feature.webp'] if os.path.exists(a + '/images/store/feature.webp') else []) + [BASE + '/assets/icons/%s.png' % a]
    for k in ('screenshot', 'softwareHelp', 'downloadUrl'):
        ld.pop(k, None)
    if shots:
        ld['screenshot'] = shots
    ld['featureList'] = specs
    if has_manual:
        ld['softwareHelp'] = {"@type": "CreativeWork", "name": name + " 取扱説明書", "url": BASE + '/' + a + '/manual/'}
    ld['releaseNotes'] = BASE + '/' + a + '/release-notes.html'
    if play:
        ld['downloadUrl'] = play.group(1)
    s = upsert_ld(s, lambda o: isinstance(o, dict) and o.get('@type') == 'MobileApplication', ld, '')
    s = upsert_ld(s, is_bc, crumbs([('ちゃ開発組', BASE + '/'), (name, u)]), '  ')
    # description
    base = lead if lead.endswith('。') else lead + '。'
    desc = '%s主な機能: %s。Android対応。' % (re.sub(r'(?<=[。！])\s+', '', base), '、'.join(specs[:3]))
    esc = html.escape(desc, quote=True)
    s = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + esc + m.group(2), s, count=1)
    s = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + esc + m.group(2), s, count=1)
    s = re.sub(r'(<meta name="twitter:description" content=")[^"]*(")', lambda m: m.group(1) + esc + m.group(2), s, count=1)
    s = enhance_meta(rel, s, imgalt=name + 'のアイコン')
    # CSS
    if '.app-facts,' in s:
        s = re.sub(r'\n    /\* アプリ情報・よくある質問[^\n]*\n.*?\.faq-more a:hover \{[^}]*\}\n', CSS, s, count=1, flags=re.S)
    else:
        s = s.replace('  </style>\n<link rel="stylesheet" href="../assets/footer.css">', CSS + '  </style>\n<link rel="stylesheet" href="../assets/footer.css">', 1)
    # アプリ情報
    links = '<a href="./manual/">取扱説明書</a> / ' if has_manual else ''
    links += '<a href="./release-notes.html">リリースノート</a> / <a href="./privacy-policy.html">プライバシーポリシー</a>'
    dist = ('<a href="%s">Google Play</a>(公開中)' % play.group(1)) if play else '開発中(Google Playでの公開前)'
    facts = '''    <!-- アプリ情報 -->
    <section class="app-facts" aria-labelledby="facts-heading">
      <div class="app-facts-heading-wrap"><h2 id="facts-heading">アプリ情報</h2></div>
      <dl class="facts-list">
        <div><dt>提供元</dt><dd><a href="../">ちゃ開発組</a></dd></div>
        <div><dt>対応OS</dt><dd>Android</dd></div>
        <div><dt>ジャンル</dt><dd>%s</dd></div>
        <div><dt>配布</dt><dd>%s</dd></div>
        <div><dt>関連ページ</dt><dd>%s</dd></div>
      </dl>
    </section>

''' % (html.escape(pill), dist, links)
    faq = ''
    if has_manual:
        fm = re.search(r'<script type="application/ld\+json">\s*(\{[^<]*"FAQPage".*?\})\s*</script>', rd(a + '/manual/index.html'), re.S)
        if fm:
            qs = json.loads(fm.group(1))['mainEntity'][:FAQ_N]
            items = ''.join('        <details><summary>%s</summary><p>%s</p></details>\n' % (
                html.escape(q['name']), html.escape(q['acceptedAnswer']['text'])) for q in qs)
            faq = '''    <!-- よくある質問 -->
    <section class="app-faq" aria-labelledby="faq-heading">
      <div class="app-faq-heading-wrap"><h2 id="faq-heading">よくある質問</h2></div>
      <div class="faq-list">
%s      </div>
      <p class="faq-more"><a href="./manual/" target="_blank" rel="noopener noreferrer">取扱説明書で詳しく見る &rarr;</a></p>
    </section>

''' % items
    block = facts + faq
    if '    <!-- アプリ情報 -->' in s:
        s = re.sub(r'    <!-- アプリ情報 -->.*?(?=    <div class="app-links-wrap">)', lambda m: block, s, count=1, flags=re.S)
    else:
        s = s.replace('    <div class="app-links-wrap">', block + '    <div class="app-links-wrap">', 1)
    wr(rel, s0, s)

# ---- トップ
s0 = rd('index.html')
s = s0
order = re.findall(r'class="app-card" href="\./([^/]+)/"', s)
items = [{"@type": "ListItem", "position": i + 1, "name": appname[a], "url": BASE + '/' + a + '/',
          "image": BASE + '/assets/icons/%s.png' % a} for i, a in enumerate(order) if a in appname]
org = {"@context": "https://schema.org", "@graph": [
    {"@type": "Organization", "@id": BASE + "/#organization", "name": "ちゃ開発組", "url": BASE + "/",
     "logo": {"@type": "ImageObject", "url": BASE + "/assets/profile.jpg"}, "image": BASE + "/assets/header.jpg",
     "description": "スマートフォン(Android)向けアプリの開発・公開を行っています。",
     "sameAs": ["https://x.com/_w6v6w_"]},
    {"@type": "CollectionPage", "@id": BASE + "/#apps", "url": BASE + "/", "name": "ちゃ開発組 公開・開発中のアプリ一覧",
     "inLanguage": "ja", "about": {"@id": BASE + "/#organization"},
     "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": items}}]}
s = upsert_ld(s, lambda o: isinstance(o, dict) and '@graph' in o, org, '  ')
s = enhance_meta('index.html', s, imgalt='ちゃ開発組')
wr('index.html', s0, s)

# ---- その他のページ(プライバシーポリシー・リリースノート・取説)
app_index = {a + '/index.html' for a in APPS}
for r, _, fs in os.walk('.'):
    if '.git' in r.split(os.sep):
        continue
    for f in fs:
        if not f.endswith('.html'):
            continue
        rel = os.path.relpath(os.path.join(r, f), '.').replace(os.sep, '/')
        if rel in ('404.html', 'index.html') or rel.startswith('google') or rel in app_index:
            continue
        s0 = rd(rel)
        s = s0
        parts = rel.split('/')
        u = url_of(rel)
        title = html.unescape(re.search(r'<title>(.*?)</title>', s, re.S).group(1)).strip()
        items = [('ちゃ開発組', BASE + '/')]
        if len(parts) == 1:
            items.append(('サイトのプライバシーポリシー', u))
        elif parts[0] not in appname:
            items.append((title.split('|')[0].strip() + ' | ' + title.split('|')[-1].strip(), u))
        else:
            a = parts[0]
            items.append((appname[a], BASE + '/' + a + '/'))
            if parts[1] == 'manual':
                items.append(('取扱説明書', BASE + '/' + a + '/manual/'))
                if len(parts) > 3 or parts[2] != 'index.html':
                    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
                    items.append((re.sub(r'^[^\w　-鿿]+', '', clean(h1.group(1) if h1 else title)).strip(), u))
            else:
                items.append((title.split('|')[0].strip(), u))
        s = upsert_ld(s, is_bc, crumbs(items), '')
        s = enhance_meta(rel, s)
        wr(rel, s0, s)

print('updated %d files' % n_changed)
