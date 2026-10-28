"""إعداد المشاركة لمكتبة جديدة — يُشغَّل مرة بعد ضبط books.json وإضافة الكتب (ويُعاد عند تغيّر العنوان).
الاستخدام:  python3 tools/configure.py https://USER.github.io/REPO/
يفعل ثلاثة أشياء:
 1) يكتب وسوم المشاركة (Open Graph) والعنوان والوصف في index.html و read.html بين علامتي SHARE.
 2) يولّد صورة المشاركة assets/og.jpg (1200×630) من العنوان والمؤلف والوصف وأغلفة حقيقية.
 3) لا يضع أرقاماً (عدد الكتب) في الصورة لأن واتساب يحتفظ بها طويلاً.
"""
import json, sys, os, re, html, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
if len(sys.argv) < 2 or not sys.argv[1].startswith("http"):
    sys.exit("اكتب رابط الموقع: python3 tools/configure.py https://USER.github.io/REPO/")
BASE = sys.argv[1].rstrip("/") + "/"
data = json.load(open(ROOT / "books.json", encoding="utf-8"))
site, books = data.get("site", {}), data.get("books", [])
title, author, sub = site.get("title", "").strip(), site.get("author", "").strip(), site.get("subtitle", "").strip()
brand = (site.get("brandTitle") or title) + ((" " + site.get("brandSub")) if site.get("brandSub") else (" " + author if author else ""))
full = title + (" — " + author if author else "")
desc = site.get("shareDescription") or ("مكتبة رقمية مجانية" + (" لـ" + author if author else "") + (": " + sub if sub else "") + "، تُقرأ بتقليب الصفحات على الجوال والكمبيوتر.")
e = lambda s: html.escape(s, quote=True)

def block(with_url):
    t = ['<!-- SHARE:START (يُولَّد تلقائياً: python3 tools/configure.py رابط-الموقع) -->',
         f'<title>{e(full)}</title>', f'<meta name="description" content="{e(desc)}">',
         '<meta property="og:type" content="website">', '<meta property="og:locale" content="ar_SA">',
         f'<meta property="og:site_name" content="{e(brand.strip())}">', f'<meta property="og:title" content="{e(full)}">',
         f'<meta property="og:description" content="{e(desc)}">']
    if with_url: t.append(f'<meta property="og:url" content="{BASE}">')
    t += [f'<meta property="og:image" content="{BASE}assets/og.jpg">', f'<meta property="og:image:secure_url" content="{BASE}assets/og.jpg">',
          '<meta property="og:image:type" content="image/jpeg">', '<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">',
          f'<meta property="og:image:alt" content="{e(full)}">', '<meta name="twitter:card" content="summary_large_image">',
          f'<meta name="twitter:title" content="{e(full)}">', f'<meta name="twitter:description" content="{e(desc)}">', f'<meta name="twitter:image" content="{BASE}assets/og.jpg">']
    if with_url: t.append(f'<link rel="canonical" href="{BASE}">')
    t.append('<!-- SHARE:END -->'); return "\n".join(t)

for name, with_url in (("index.html", True), ("read.html", False)):
    p = ROOT / name; s = p.read_text(encoding="utf-8")
    s, n = re.subn(r"<!-- SHARE:START.*?<!-- SHARE:END -->", lambda m: block(with_url), s, flags=re.S)
    if not n: sys.exit(f"لم أجد علامتي SHARE في {name}")
    p.write_text(s, encoding="utf-8"); print("✓ وسوم المشاركة:", name)

# اختيار 3 أغلفة: الأكبر صفحاتٍ في كل مجموعة، ثم الأكبر عموماً — الأكبر في المنتصف
withc = [b for b in books if b.get("cover") and (ROOT / b["cover"]).exists()]
cats = []
for b in books:
    if b.get("category") and b["category"] not in cats: cats.append(b["category"])
feat = []
for c in cats:
    l = sorted([b for b in withc if b.get("category") == c], key=lambda b: -(int(b.get("pages") or 0)))
    if l and l[0] not in feat: feat.append(l[0])
for b in sorted(withc, key=lambda b: -(int(b.get("pages") or 0))):
    if len(feat) >= 3: break
    if b not in feat: feat.append(b)
feat = sorted(feat[:3], key=lambda b: int(b.get("pages") or 0))
if len(feat) == 3:
    fan = ('<div class="fan"><div class="shadow"></div><div class="line"></div>'
           + "".join(f'<img class="{c}" src="../{e(b["cover"])}">' for c, b in zip(("l", "r", "c"), feat)) + "</div>")
    bodyc = ""
else:
    fan, bodyc = "", "nocovers"
tpl = (ROOT / "tools/og-template.html").read_text(encoding="utf-8")
out = tpl.replace("@@FAN@@", fan).replace("@@BODYCLASS@@", bodyc).replace("@@TITLE@@", e(title)).replace("@@AUTHOR@@", e(author)).replace("@@SUBTITLE@@", e(sub)).replace("@@THEME@@", ('<script src="../assets/common.js"></script><script>Lib.applyTheme(' + json.dumps(site.get("theme"), ensure_ascii=False) + ', {preview:true})</script>') if site.get("theme") else "")
tmp = ROOT / "tools/_og.html"; tmp.write_text(out, encoding="utf-8")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 630})
        pg.goto(tmp.as_uri()); pg.wait_for_timeout(1500)
        pg.screenshot(path=str(ROOT / "tools/_og.png")); br.close()
    from PIL import Image
    Image.open(ROOT / "tools/_og.png").convert("RGB").save(ROOT / "assets/og.jpg", quality=86, optimize=True)
    os.remove(ROOT / "tools/_og.png"); print("✓ صورة المشاركة: assets/og.jpg", "(بدون أغلفة)" if bodyc else "")
except Exception as ex:
    print("⚠ تعذّر توليد الصورة تلقائياً:", ex, "— افتح tools/_og.html وصوّرها 1200×630")
else:
    os.remove(tmp)

# أيقونة الشاشة الرئيسية للآيفون بألوان الهوية (assets/apple-touch-icon.png 180×180)
if site.get("theme"):
    try:
        from playwright.sync_api import sync_playwright
        ic = ROOT / "tools/_icon.html"
        ic.write_text('<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="../assets/style.css"><script src="../assets/common.js"></script>'
            '<style>html,body{margin:0;width:180px;height:180px;overflow:hidden;background:var(--t-primary)}svg{display:block}</style></head><body>'
            '<svg viewBox="0 0 64 64" width="180" height="180"><rect width="64" height="64" style="fill:var(--t-primary)"/>'
            '<path d="M10 22c8-3.5 15-2.5 22 2.5v27c-7-5-14-6-22-2.5z M54 22c-8-3.5-15-2.5-22 2.5v27c7-5 14-6 22-2.5z" style="fill:var(--t-accent)"/>'
            '<path d="M32 7l2.4 4.9 5.4.8-3.9 3.8.9 5.4L32 19.4l-4.8 2.5.9-5.4-3.9-3.8 5.4-.8z" style="fill:var(--t-bg)"/></svg>'
            '<script>Lib.applyTheme(' + json.dumps(site.get("theme"), ensure_ascii=False) + ', {preview:true})</script></body></html>', encoding="utf-8")
        with sync_playwright() as pw:
            br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 180, "height": 180})
            pg.goto(ic.as_uri()); pg.wait_for_timeout(500); pg.screenshot(path=str(ROOT / "assets/apple-touch-icon.png")); br.close()
        os.remove(ic); print("✓ أيقونة الآيفون بألوان الهوية: assets/apple-touch-icon.png")
    except Exception as ex:
        print("⚠ تعذّر توليد أيقونة الآيفون:", ex)
