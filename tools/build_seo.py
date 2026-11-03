#!/usr/bin/env python3
"""
الظهور في محركات البحث ونماذج الذكاء الاصطناعي (v37)
يولّد من books.json وملفات PDF:
  1) kitab/<id>.html  صفحة نصية ثابتة لكل كتاب (تُحذف صفحة أي كتاب انحذف)
  2) قسم ثابت في index.html بين <!-- SEO:START --> و <!-- SEO:END -->
  3) sitemap.xml   4) llms.txt
التشغيل:  python3 tools/build_seo.py [رابط-الموقع]
(يشتغل تلقائياً عبر .github/workflows/seo.yml مع كل تغيير في books.json أو مجلد books)
"""
import datetime, html, json, os, re, sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

PRESETS = {
  "emerald": {"primary": "#164E3B", "accent": "#C6A15B", "bg": "#F7F3E8", "ink": "#26332D"},
  "navy": {"primary": "#1E3A5F", "accent": "#C9A45C", "bg": "#F5F3EE", "ink": "#1F2933"},
  "maroon": {"primary": "#6B1F2A", "accent": "#D2A85A", "bg": "#FAF5EE", "ink": "#2E2224"},
  "coffee": {"primary": "#4A3426", "accent": "#C89B5A", "bg": "#F8F2E8", "ink": "#2D241D"},
  "teal": {"primary": "#0F4C5C", "accent": "#E3B04B", "bg": "#F3F6F4", "ink": "#1E2B2F"},
  "charcoal": {"primary": "#2F3A45", "accent": "#E08A3C", "bg": "#F7F6F3", "ink": "#22272B"},
}
def hex_ok(h): return isinstance(h, str) and re.fullmatch(r"#?[0-9a-fA-F]{6}", h.strip()) is not None
def to_rgb(h): h = h.strip().replace("#", ""); return [int(h[i:i+2], 16) for i in (0, 2, 4)]
def _r(v):  # Math.round
    import math; return math.floor(v + 0.5)
def to_hex(c): return "#" + "".join(format(_r(max(0, min(255, v))), "02x") for v in c)
def mix(a, b, t): return [v + (b[i] - v) * t for i, v in enumerate(a)]
def lum(c):
    def f(v):
        v /= 255; return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])
def contrast(a, b): x, y = lum(a), lum(b); return (max(x, y) + 0.05) / (min(x, y) + 0.05)
BLACK, WHITE = [0, 0, 0], [255, 255, 255]
def derive(t):
    d = PRESETS["emerald"]
    g = lambda k: to_rgb(t[k] if hex_ok(t.get(k)) else d[k])
    P, A, B, I = g("primary"), g("accent"), g("bg"), g("ink")
    for _ in range(20):
        if contrast(WHITE, P) >= 5.5: break
        P = mix(P, BLACK, 0.08)
    for _ in range(20):
        if lum(B) >= 0.8: break
        B = mix(B, WHITE, 0.15)
    for _ in range(20):
        if contrast(I, B) >= 9: break
        I = mix(I, BLACK, 0.12)
    Pd = mix(P, BLACK, 0.36)
    for _ in range(20):
        if contrast(A, Pd) >= 3.2: break
        A = mix(A, WHITE, 0.1)
    At = mix(A, BLACK, 0.3)
    for _ in range(20):
        if contrast(At, B) >= 4.6: break
        At = mix(At, BLACK, 0.08)
    rgb = lambda c: " ".join(str(_r(x)) for x in c)
    H_ = to_hex
    v = {
      "primary": H_(P), "primary-rgb": rgb(P), "primary-l": H_(mix(P, WHITE, 0.06)), "primary-2": H_(mix(P, BLACK, 0.25)), "primary-2-rgb": rgb(mix(P, BLACK, 0.25)),
      "primary-d": H_(Pd), "primary-d-rgb": rgb(Pd), "primary-dd": H_(mix(P, BLACK, 0.52)), "primary-dd-rgb": rgb(mix(P, BLACK, 0.52)),
      "stage": H_(mix(P, BLACK, 0.6)), "stage-rgb": rgb(mix(P, BLACK, 0.6)), "sheet": H_(mix(mix(P, BLACK, 0.55), I, 0.12)),
      "zoom": H_(mix(P, BLACK, 0.68)), "annbar-rgb": rgb(mix(P, BLACK, 0.5)),
      "accent": H_(A), "accent-rgb": rgb(A), "accent-2-rgb": rgb(A), "accent-m": H_(mix(A, BLACK, 0.15)), "accent-text": H_(At),
      "bg": H_(B), "bg-rgb": rgb(B), "bg-2": H_(mix(B, A, 0.18)), "card": H_(mix(B, WHITE, 0.7)), "soft": H_(mix(B, A, 0.13)),
      "line": H_(mix(mix(B, A, 0.22), I, 0.04)), "line-2": H_(mix(mix(B, A, 0.2), I, 0.05)),
      "ink": H_(I), "ink-rgb": rgb(I), "muted": H_(mix(I, B, 0.3)), "muted-2": H_(mix(I, B, 0.33)),
      "on-dark-2": H_(mix(B, A, 0.18)), "on-dark-3": H_(mix(B, A, 0.1)), "placeholder": H_(mix(I, B, 0.45)),
      "chip": H_(mix(B, I, 0.04)), "chip-h": H_(mix(B, A, 0.2)), "tint": H_(mix(B, A, 0.18)), "tint-2": H_(mix(B, A, 0.05)),
      "pg": H_(mix(B, WHITE, 0.45)), "pg-2": H_(mix(B, A, 0.1)), "pg-ink": H_(mix(mix(A, B, 0.35), I, 0.15)),
    }
    tint = lambda a, i: H_(mix(mix(B, A, a), I, i))
    v.update({"fan": H_(mix(P, BLACK, 0.45)), "line-h": tint(0.45, 0.07), "line-h2": tint(0.42, 0.07), "frame": tint(0.1, 0.02),
      "frame-2": tint(0.2, 0.03), "frame-h": tint(0.22, 0.03), "frame-h2": tint(0.32, 0.04), "dot": tint(0.5, 0.25)})
    Hh = to_rgb(t["highlight"]) if hex_ok(t.get("highlight")) else mix(A, WHITE, 0.25)
    for _ in range(20):
        if contrast(Hh, P) >= 4.5: break
        Hh = mix(Hh, WHITE, 0.12)
    v["highlight"] = H_(Hh)
    from urllib.parse import quote
    enc = quote(v["accent"], safe="")
    v["pat"] = f"""url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='84' height='84' viewBox='0 0 84 84'%3E%3Cg fill='none' stroke='{enc}' stroke-width='.7' stroke-opacity='.22'%3E%3Cpath d='M42 18l7 17 17 7-17 7-7 17-7-17-17-7 17-7z'/%3E%3Crect x='27' y='27' width='30' height='30' transform='rotate(45 42 42)'/%3E%3Ccircle cx='42' cy='42' r='5'/%3E%3Cpath d='M0 0l12 12M84 0L72 12M0 84l12-12M84 84L72 72'/%3E%3C/g%3E%3C/svg%3E")"""
    return v
def theme_css(theme):
    if not isinstance(theme, dict): return ""
    t = dict(PRESETS[theme["preset"]], **theme) if theme.get("preset") in PRESETS else theme
    if not any(hex_ok(t.get(k)) for k in ("primary", "accent", "bg", "ink")): return ""
    v = derive(t)
    return ":root:root{" + ";".join(f"--t-{k}:{x}" for k, x in v.items()) + "}"

# ---------- أدوات ----------
e = lambda s: html.escape(str(s or ""), quote=True)
plain = lambda s: re.sub(r"[ً-ْٰ]", "", str(s or "")).strip()
AR_DIG = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
ar = lambda n: f"{int(n):,}".replace(",", "٬").translate(AR_DIG)
MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
def ar_date(s):
    try: d = datetime.date.fromisoformat(str(s)[:10])
    except Exception: return ""
    return f"{ar(d.day)} {MONTHS[d.month - 1]} {str(d.year).translate(AR_DIG)}م"
# نفس قاعدة Lib.plural في common.js
WORDS = {"book": ["كتاب", "كتابان", "كتب", "كتاباً", "كتاب"], "page": ["صفحة", "صفحتان", "صفحات", "صفحة", "صفحة"]}
def plural(n, w):
    f = WORDS[w]; n = abs(round(float(n or 0))); m = n % 100
    if n == 1: return f[0]
    if n == 2: return f[1]
    if n >= 100 and m <= 2: return f[4]
    if m >= 11: return f[3]
    return f[2]
def count(n, w):  # «٣٧ صفحة» — «صفحة واحدة» — «صفحتان»
    n = int(n)
    if n == 1: return {"book": "كتاب واحد", "page": "صفحة واحدة"}[w]
    if n == 2: return plural(2, w)
    return f"{ar(n)} {plural(n, w)}"

def base_url():
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"): u = sys.argv[1]
    elif os.environ.get("GITHUB_REPOSITORY"):
        o, r = os.environ["GITHUB_REPOSITORY"].split("/", 1)
        u = f"https://{o.lower()}.github.io/" + ("" if r.lower() == f"{o.lower()}.github.io" else r + "/")
    else:
        m = re.search(r'<link rel="canonical" href="([^"]+)"', Path("index.html").read_text(encoding="utf-8"))
        if not m: sys.exit("اكتب رابط الموقع: python3 tools/build_seo.py https://USER.github.io/REPO/")
        u = m.group(1)
    return u.rstrip("/") + "/"

# ---------- مقتطف من محتوى الكتاب (فقط إذا النص المستخرج سليم) ----------
# خطوط PDF العربية كثيراً ما تُخرج نصاً مشوّهاً (اهلل بدل الله، يف بدل في، األوىل…)؛ إذا ظهر أي أثر لذلك لا نضع شيئاً.
BAD = re.compile(r"اهلل|هلل|عبدهللا|األ|اإل|اآل|(?<!\S)يف(?!\S)|ىل(?!\S)|ىن(?!\S)|[�åﭐ-﷿ﹰ-﻿-]")
def excerpt(pdf):
    try: import pymupdf
    except ImportError:
        try: import fitz as pymupdf
        except ImportError: return None
    try:
        doc = pymupdf.open(pdf)
        pages = [doc[i].get_text() for i in range(min(8, len(doc)))]
    except Exception: return None
    raw = "\n".join(pages)
    words = re.findall(r"[ء-ي]{2,}", raw)
    if len(words) < 60 or BAD.search(raw): return None
    # لا نقبل نصاً معكوس الأسطر أو مقطّع الحروف: معظم الكلمات لازم تكون كلمات عربية طبيعية
    if sum(len(w) == 1 for w in re.findall(r"[ء-ي]+", raw)) > 0.08 * len(words): return None
    clean = lambda s: re.sub(r"\s+", " ", re.sub(r"[ـ‎‏‪-‮]", "", s)).strip()
    toc, intro = [], []
    for p in pages[1:]:
        lines = [clean(x) for x in p.splitlines()]
        lines = [x for x in lines if x and not re.fullmatch(r"[\d٠-٩\s.\-–*]+", x)]
        if any(re.search(r"^(الفهرس|فهرس|المحتويات|فهرس الموضوعات)$", x) for x in lines):
            for x in lines:
                t = clean(re.sub(r"[.\s…]*[\d٠-٩]+\s*$", "", x))
                if t and t not in ("الفهرس", "فهرس", "المحتويات", "فهرس الموضوعات") and len(t) <= 70 and t not in toc: toc.append(t)
        else:
            intro.extend(x for x in lines if x not in intro)
    text = clean(" ".join(intro))
    if len(text) > 1500:
        cut = text[:1500]; k = max(cut.rfind("."), cut.rfind("،"), cut.rfind(" "))
        text = cut[:k if k > 1000 else 1500].rstrip(" ،") + "…"
    if len(text) < 120 and not toc: return None
    return {"intro": text, "toc": toc[:40]}

# ---------- القوالب ----------
def size(path):  # أبعاد الغلاف الحقيقية حتى لا تتحرك الصفحة أثناء التحميل
    try:
        from PIL import Image
        w, h = Image.open(path).size; return f' width="{w}" height="{h}"'
    except Exception: return ""
BRAND_SVG = '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M10 22c8-3.5 15-2.5 22 2.5v27c-7-5-14-6-22-2.5z M54 22c-8-3.5-15-2.5-22 2.5v27c7-5 14-6 22-2.5z" style="fill:var(--t-accent)"/><path d="M32 7l2.4 4.9 5.4.8-3.9 3.8.9 5.4L32 19.4l-4.8 2.5.9-5.4-3.9-3.8 5.4-.8z" style="fill:var(--t-bg)"/></svg>'
CREDIT = '<div class="credit">تصميم وإعداد: <b>محمد الشهري</b><span class="sep">•</span>للتواصل: <a href="https://wa.me/966564824329" target="_blank" rel="noopener" dir="ltr">0564824329</a></div>'
PAGE_CSS = """
body.kb-page{display:flex;flex-direction:column;min-height:100vh}.kb-page .kb{flex:1}
.kb{padding:40px 0 8px}
.kb-info{max-width:640px}
.kb .crumb{font-size:14px;color:var(--muted);margin:0 0 22px}
.kb .crumb a{color:var(--gold);text-decoration:none;font-weight:600}
.kb-grid{display:grid;grid-template-columns:minmax(0,300px) minmax(0,1fr);gap:44px;align-items:start}
.kb-cover{margin:0;border-radius:6px 14px 14px 6px;overflow:hidden;background:var(--t-card);box-shadow:0 22px 44px -22px rgb(var(--t-primary-dd-rgb) / .55),0 0 0 1px var(--line)}
.kb-cover img{display:block;width:100%;height:auto}
.kb h1{font-family:var(--display);font-weight:700;font-size:clamp(34px,5vw,52px);line-height:1.45;color:var(--emerald);margin:0 0 6px}
.kb .by{font-size:17px;color:var(--gold);margin:0 0 22px;font-weight:500}
.kb dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:10px 18px;margin:0 0 28px;padding:18px 20px;background:var(--t-card);border:1px solid var(--line);border-radius:var(--r)}
.kb dt{color:var(--muted);font-size:14.5px}
.kb dd{margin:0;font-weight:600;color:var(--ink)}
.kb dd a{color:inherit;text-decoration:none}
.kb .desc{line-height:2;margin:0 0 26px}
.kb-act{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:center}
.kb-read{display:inline-flex;align-items:center;gap:10px;background:var(--emerald);color:#fff;text-decoration:none;font-weight:600;font-size:17px;padding:14px 28px;border-radius:999px;box-shadow:0 12px 26px -12px rgb(var(--t-primary-rgb) / .7);transition:background .2s,transform .2s}
.kb-read:hover{background:var(--emerald-d);transform:translateY(-1px)}
.kb-read svg{width:20px;height:20px}
.kb-back{color:var(--gold);font-weight:600;text-decoration:none}
.kb-back:hover{text-decoration:underline}
.kb-ex{margin:44px 0 0;padding:26px 28px;background:var(--t-card);border:1px solid var(--line);border-radius:var(--r)}
.kb-ex h2{font-family:var(--display);color:var(--emerald);font-size:26px;margin:0 0 12px}
.kb-ex h3{font-size:16px;color:var(--gold);margin:20px 0 8px}
.kb-ex p{line-height:2.1;margin:0}
.kb-ex ul{margin:0;padding-inline-start:20px;columns:2;column-gap:32px;line-height:2}
.kb-foot{margin-top:56px;background:var(--emerald-dd)}
@media (max-width:760px){.kb{padding-top:24px}.kb-grid{grid-template-columns:minmax(0,1fr);gap:26px;text-align:center}.kb-cover{max-width:230px;margin:0 auto}
  .kb dl{text-align:start}.kb-act{justify-content:center}.kb-ex{text-align:start;padding:20px 18px}.kb-ex ul{columns:1}.kb-foot .foot-bot{padding-bottom:22px}}
"""

def book_page(b, site, lib, base, theme, ver, ex):
    title, author, cat = b["title"], (b.get("author") or site.get("author") or "").strip(), (b.get("category") or "").strip()
    url, cover = f"{base}kitab/{quote(b['id'])}.html", (base + quote(b["cover"])) if b.get("cover") else base + "assets/og.jpg"
    pages = int(b.get("pages") or 0); desc_field = (b.get("description") or b.get("desc") or "").strip()
    head_title = f"{title} — {author} | {lib}" if author else f"{title} | {lib}"
    meta = f"كتاب «{title}»" + (f" — {author}" if author else "") + (f"، من تصنيف {cat}" if cat else "") + (f"، في {count(pages, 'page')}" if pages else "") + f". اقرأه مجاناً بتقليب الصفحات في {lib}."
    if desc_field: meta = desc_field + " — " + meta
    ld = {"@context": "https://schema.org", "@type": "Book", "name": title, "inLanguage": "ar", "url": url, "image": cover,
          "isPartOf": {"@type": "WebSite", "name": lib, "url": base}}
    if author: ld["author"] = {"@type": "Person", "name": author}
    if pages: ld["numberOfPages"] = pages
    if cat: ld["genre"] = cat
    if desc_field: ld["description"] = desc_field
    if b.get("added"): ld["dateCreated"] = str(b["added"])[:10]
    ld_json = json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/")
    rows = []
    if author: rows.append(("المؤلف", e(author)))
    if cat: rows.append(("التصنيف", f'<a href="../#library">{e(cat)}</a>'))
    if pages: rows.append(("عدد الصفحات", e(count(pages, "page"))))
    if b.get("added") and ar_date(b["added"]): rows.append(("تاريخ الإضافة", f'<time datetime="{e(str(b["added"])[:10])}">{ar_date(b["added"])}</time>'))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    exh = ""
    if ex:
        exh = '<section class="kb-ex" aria-labelledby="exT"><h2 id="exT">من محتوى الكتاب</h2>'
        if ex["intro"]: exh += f"<p>{e(ex['intro'])}</p>"
        if ex["toc"]: exh += "<h3>من موضوعات الكتاب</h3><ul>" + "".join(f"<li>{e(t)}</li>" for t in ex["toc"]) + "</ul>"
        exh += "</section>"
    read = f"../read.html?id={quote(b['id'])}"
    style = f'<style id="lib-theme">{theme}</style>\n' if theme else ""
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(head_title)}</title>
<meta name="description" content="{e(meta)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="book">
<meta property="og:locale" content="ar_SA">
<meta property="og:site_name" content="{e(lib)}">
<meta property="og:title" content="{e(title + (' — ' + author if author else ''))}">
<meta property="og:description" content="{e(meta)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(cover)}">
<meta property="og:image:alt" content="{e(title)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(meta)}">
<meta name="twitter:image" content="{e(cover)}">
<script type="application/ld+json">
{ld_json}
</script>
<link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">
<link rel="stylesheet" href="../assets/style.css?v={ver}">
<link rel="stylesheet" href="../assets/home.css?v={ver}">
{style}<style>{PAGE_CSS.strip()}</style>
</head>
<body class="home kb-page">
<header class="topbar">
  <div class="wrap">
    <a class="brand" href="../" aria-label="الصفحة الرئيسية">
      <span class="brand-mark">{BRAND_SVG}</span>
      <span class="brand-txt"><b>{e(site.get("brandTitle") or lib)}</b><small>{e(site.get("brandSub") or site.get("author") or "")}</small></span>
    </a>
  </div>
</header>
<main class="kb">
  <div class="wrap">
    <p class="crumb"><a href="../">{e(lib)}</a>{' ‹ ' + e(cat) if cat else ''}</p>
    <article class="kb-grid">
      <figure class="kb-cover"><img src="../{e(b.get('cover') or 'assets/og.jpg')}" alt="{e(title)}"{size(b.get('cover'))}></figure>
      <div class="kb-info">
        <h1>{e(title)}</h1>
        {f'<p class="by">{e(author)}</p>' if author else ''}
        {f'<p class="desc">{e(desc_field)}</p>' if desc_field else ''}
        <dl>{dl}</dl>
        <div class="kb-act">
          <a class="kb-read" href="{e(read)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 5.5C5 4 8.5 4.2 12 6.5v13c-3.5-2.3-7-2.5-10-1z M22 5.5C19 4 15.5 4.2 12 6.5v13c3.5-2.3 7-2.5 10-1z"/></svg>اقرأ الكتاب</a>
          <a class="kb-back" href="../">العودة للمكتبة ←</a>
        </div>
      </div>
    </article>
    {exh}
  </div>
</main>
<footer class="foot kb-foot"><div class="foot-bot"><div class="wrap">{CREDIT}</div></div></footer>
</body>
</html>
"""

def seo_block(site, lib, books, cats):
    # قائمة ثابتة داخل <noscript> في مكان رف الكتب (#shelf): تظهر لمن لا يشغّل الجافاسكربت ولقرّاء HTML (نماذج الذكاء الاصطناعي)،
    # ولا تُرسم إطلاقاً للزائر العادي — بدون أي إخفاء بالـ CSS وبدون وميض.
    author = site.get("author") or ""
    L = ['<!-- SEO:START (يُولَّد تلقائياً: python3 tools/build_seo.py — لا تعدّل هنا) -->',
         '<noscript>',
         '<style>#shelf>noscript{display:block;grid-column:1/-1}.seo-ns{line-height:1.9}.seo-ns h2{font-family:var(--display);color:var(--emerald);margin:0 0 6px}.seo-ns h3{color:var(--gold);margin:22px 0 6px;font-size:18px}.seo-ns ul{margin:0;padding-inline-start:22px}.seo-ns a{color:var(--ink)}</style>',
         '<section class="seo-ns" aria-label="قائمة الكتب">',
         f'<h2>{e(lib)}{" — " + e(author) if author else ""}</h2>',
         f'<p>{e(site.get("subtitle") or "مكتبة رقمية")}: {e(count(len(books), "book"))} تُقرأ مجاناً بتقليب الصفحات على الجوال والكمبيوتر.</p>']
    for c in cats:
        L.append(f'<h3>{e(c or "أخرى")}</h3><ul>' + "".join(f'<li><a href="kitab/{quote(b["id"])}.html">{e(b["title"])}</a></li>' for b in books if (b.get("category") or "") == c) + "</ul>")
    L += ['</section>', '</noscript>', '<!-- SEO:END -->']
    return "\n".join(L)

def main():
    data = json.loads(Path("books.json").read_text(encoding="utf-8"))
    site = data.get("site") or {}
    books = [b for b in data.get("books") or [] if b.get("id") and b.get("title") and re.fullmatch(r"[\w-]+", b["id"])]
    base = base_url()
    lib = plain(site.get("title")) or plain(site.get("brandTitle")) or "المكتبة"
    theme = theme_css(site.get("theme"))
    idx = Path("index.html").read_text(encoding="utf-8")
    m = re.search(r'assets/style\.css\?v=(\d+)', idx); ver = m.group(1) if m else "1"
    # التصنيفات بنفس ترتيب الموقع، ثم أي تصنيف غير مسجّل، ثم «أخرى»
    cats = [c for c in site.get("categories") or [] if any((b.get("category") or "") == c for b in books)]
    cats += sorted({b.get("category") or "" for b in books} - set(cats) - {""})
    if any(not b.get("category") for b in books): cats.append("")
    # 1) صفحات الكتب
    out = Path("kitab"); out.mkdir(exist_ok=True)
    keep, n_ex = set(), 0
    for b in books:
        ex = excerpt(b["file"]) if b.get("file") and Path(b["file"]).exists() else None
        n_ex += bool(ex)
        p = out / f"{b['id']}.html"; keep.add(p.name)
        s = book_page(b, site, lib, base, theme, ver, ex)
        if not p.exists() or p.read_text(encoding="utf-8") != s: p.write_text(s, encoding="utf-8")
    removed = [p.name for p in out.glob("*.html") if p.name not in keep]
    for name in removed: (out / name).unlink()
    # 2) القائمة الثابتة في index.html: داخل رف الكتب <main id="shelf"> (يستبدلها العرض المعتاد للزائر)
    blk = seo_block(site, lib, books, cats)
    new = re.sub(r"\n?<!-- SEO:START.*?<!-- SEO:END -->\n?", "", idx, flags=re.S)  # إزالة أي نسخة سابقة أينما كانت
    m = re.search(r'(<main class="shelf" id="shelf"[^>]*>)(</main>)', new)
    if not m: sys.exit('لم أجد <main class="shelf" id="shelf"> فارغاً في index.html')
    new = new[:m.end(1)] + "\n" + blk + "\n" + new[m.start(2):]
    if new != idx: Path("index.html").write_text(new, encoding="utf-8")
    # 3) sitemap.xml
    day = lambda b: str(b.get("added") or b.get("date") or "")[:10]
    last = max([day(b) for b in books if day(b)] or [datetime.date.today().isoformat()])
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
          f"  <url><loc>{e(base)}</loc><lastmod>{last}</lastmod></url>"]
    sm += [f"  <url><loc>{e(base)}kitab/{quote(b['id'])}.html</loc>" + (f"<lastmod>{day(b)}</lastmod>" if day(b) else "") + "</url>" for b in books]
    sm.append("</urlset>")
    Path("sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    # 4) llms.txt
    author = site.get("author") or ""
    lt = [f"# {lib}" + (f" — {author}" if author else ""), "",
          f"> {site.get('subtitle') or 'مكتبة رقمية'}{' — ' + author if author else ''}، فيها {count(len(books), 'book')} باللغة العربية.",
          "> تُقرأ الكتب مجاناً على الموقع بتقليب الصفحات؛ ولكل كتاب صفحة فيها بياناته ورابط قراءته.", "",
          f"- الموقع: {base}"]
    for c in cats:
        lt += ["", f"## {c or 'أخرى'}", ""]
        for b in books:
            if (b.get("category") or "") != c: continue
            info = [x for x in [b.get("author") if b.get("author") and b.get("author") != author else "", c, count(b["pages"], "page") if b.get("pages") else ""] if x]
            lt.append(f"- [{b['title']}]({base}kitab/{quote(b['id'])}.html): " + "، ".join(info))
    Path("llms.txt").write_text("\n".join(lt) + "\n", encoding="utf-8")
    print(f"✓ {len(books)} صفحة كتاب في kitab/ (مع مقتطف: {n_ex})" + (f" — حُذفت: {', '.join(removed)}" if removed else ""))
    print(f"✓ index.html (قسم SEO) • sitemap.xml • llms.txt — {base}")

if __name__ == "__main__":
    main()
