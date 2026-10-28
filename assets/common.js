// أدوات مشتركة بين صفحات المكتبة
(function () {
  const BOOK_EXT = /\.pdf$/i;
  const IMG_EXT = /\.(jpe?g|png|webp)$/i;

  // استنتاج اسم الحساب والمستودع من رابط GitHub Pages تلقائياً
  function repoInfo() {
    const host = location.hostname;
    const m = host.match(/^([^.]+)\.github\.io$/i);
    if (!m) return null;
    const owner = m[1];
    const first = location.pathname.split("/").filter(Boolean)[0];
    const repo = first && !/\.html?$/i.test(first) ? first : host;
    return { owner, repo };
  }

  function titleFromFile(name) {
    return decodeURIComponent(name).replace(BOOK_EXT, "").replace(/[_-]+/g, " ").trim();
  }

  async function fetchJSON(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }

  // يقرأ قائمة الكتب، ويضيف تلقائياً أي ملف PDF رُفع مباشرة إلى مجلد books دون تسجيله
  async function loadLibrary() {
    let data = { site: {}, books: [] };
    try { data = await fetchJSON("books.json?v=" + Date.now()); } catch (e) { console.warn("books.json", e); }
    data.site = data.site || {};
    data.books = Array.isArray(data.books) ? data.books : [];

    const info = repoInfo();
    if (info && data.site.autoDetect !== false) {
      try {
        const api = `https://api.github.com/repos/${info.owner}/${info.repo}/contents/`;
        const [bk, cv] = await Promise.all([
          fetchJSON(api + "books"),
          fetchJSON(api + "covers").catch(() => []),
        ]);
        const known = new Set(data.books.map((b) => b.file));
        const covers = {};
        (cv || []).forEach((f) => { if (IMG_EXT.test(f.name)) covers[f.name.replace(IMG_EXT, "")] = "covers/" + f.name; });
        (bk || []).forEach((f) => {
          if (f.type !== "file" || !BOOK_EXT.test(f.name)) return;
          const file = "books/" + f.name;
          if (known.has(file)) return;
          const base = f.name.replace(BOOK_EXT, "");
          data.books.push({ id: "", title: titleFromFile(f.name), file, cover: covers[base] || "", auto: true });
        });
      } catch (e) { /* القائمة الأساسية تكفي */ }
    }
    try { applyTheme(data.site.theme); } catch (e) { console.warn("theme", e); }
    return data;
  }

  function readerUrl(b) {
    return b.id ? "read.html?id=" + encodeURIComponent(b.id) : "read.html?file=" + encodeURIComponent(b.file);
  }

  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del(k) { try { localStorage.removeItem(k); } catch (e) {} },
  };


  // ===== الهوية اللونية لكل عميل: books.json → site.theme = { primary, accent, bg, ink } =====
  // تُعطى أربعة ألوان فقط، وتُشتق منها كل الدرجات مع ضمان وضوح النص العربي. بدون theme تبقى الهوية الافتراضية كما هي.
  const PRESETS = {
    emerald: { name: "زمردي (الافتراضي)", primary: "#164E3B", accent: "#C6A15B", bg: "#F7F3E8", ink: "#26332D" },
    navy:    { name: "كحلي", primary: "#1E3A5F", accent: "#C9A45C", bg: "#F5F3EE", ink: "#1F2933" },
    maroon:  { name: "عنّابي", primary: "#6B1F2A", accent: "#D2A85A", bg: "#FAF5EE", ink: "#2E2224" },
    coffee:  { name: "بنّي قهوة", primary: "#4A3426", accent: "#C89B5A", bg: "#F8F2E8", ink: "#2D241D" },
    teal:    { name: "فيروزي", primary: "#0F4C5C", accent: "#E3B04B", bg: "#F3F6F4", ink: "#1E2B2F" },
    charcoal:{ name: "فحمي وبرتقالي", primary: "#2F3A45", accent: "#E08A3C", bg: "#F7F6F3", ink: "#22272B" },
  };
  const hexOk = (h) => typeof h === "string" && /^#?[0-9a-f]{6}$/i.test(h.trim());
  const toRgb = (h) => { h = h.trim().replace("#", ""); return [0, 2, 4].map((i) => parseInt(h.substr(i, 2), 16)); };
  const toHex = (c) => "#" + c.map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join("");
  const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t); // t = نسبة اللون الثاني
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const contrast = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const BLACK = [0, 0, 0], WHITE = [255, 255, 255];
  function deriveTheme(t) {
    const d = PRESETS.emerald;
    let P = toRgb(hexOk(t.primary) ? t.primary : d.primary), A = toRgb(hexOk(t.accent) ? t.accent : d.accent);
    let B = toRgb(hexOk(t.bg) ? t.bg : d.bg), I = toRgb(hexOk(t.ink) ? t.ink : d.ink);
    // ضمانات الوضوح: الأساسي غامق بما يكفي للنص الأبيض، والخلفية فاتحة، والنص غامق عليها
    for (let k = 0; k < 20 && contrast(WHITE, P) < 5.5; k++) P = mix(P, BLACK, 0.08);
    for (let k = 0; k < 20 && lum(B) < 0.8; k++) B = mix(B, WHITE, 0.15);
    for (let k = 0; k < 20 && contrast(I, B) < 9; k++) I = mix(I, BLACK, 0.12);
    const Pd = mix(P, BLACK, 0.36);
    for (let k = 0; k < 20 && contrast(A, Pd) < 3.2; k++) A = mix(A, WHITE, 0.1);
    let At = mix(A, BLACK, 0.3);
    for (let k = 0; k < 20 && contrast(At, B) < 4.6; k++) At = mix(At, BLACK, 0.08);
    const rgb = (c) => c.map(Math.round).join(" ");
    const v = {
      "primary": toHex(P), "primary-rgb": rgb(P), "primary-l": toHex(mix(P, WHITE, 0.06)), "primary-2": toHex(mix(P, BLACK, 0.25)), "primary-2-rgb": rgb(mix(P, BLACK, 0.25)),
      "primary-d": toHex(Pd), "primary-d-rgb": rgb(Pd), "primary-dd": toHex(mix(P, BLACK, 0.52)), "primary-dd-rgb": rgb(mix(P, BLACK, 0.52)),
      "stage": toHex(mix(P, BLACK, 0.6)), "stage-rgb": rgb(mix(P, BLACK, 0.6)), "sheet": toHex(mix(mix(P, BLACK, 0.55), I, 0.12)),
      "zoom": toHex(mix(P, BLACK, 0.68)), "annbar-rgb": rgb(mix(P, BLACK, 0.5)),
      "accent": toHex(A), "accent-rgb": rgb(A), "accent-2-rgb": rgb(A), "accent-m": toHex(mix(A, BLACK, 0.15)), "accent-text": toHex(At),
      "bg": toHex(B), "bg-rgb": rgb(B), "bg-2": toHex(mix(B, A, 0.18)), "card": toHex(mix(B, WHITE, 0.7)), "soft": toHex(mix(B, A, 0.13)),
      "line": toHex(mix(mix(B, A, 0.22), I, 0.04)), "line-2": toHex(mix(mix(B, A, 0.2), I, 0.05)),
      "ink": toHex(I), "ink-rgb": rgb(I), "muted": toHex(mix(I, B, 0.3)), "muted-2": toHex(mix(I, B, 0.33)),
      "on-dark-2": toHex(mix(B, A, 0.18)), "on-dark-3": toHex(mix(B, A, 0.1)), "placeholder": toHex(mix(I, B, 0.45)),
      "chip": toHex(mix(B, I, 0.04)), "chip-h": toHex(mix(B, A, 0.2)), "tint": toHex(mix(B, A, 0.18)), "tint-2": toHex(mix(B, A, 0.05)),
      "pg": toHex(mix(B, WHITE, 0.45)), "pg-2": toHex(mix(B, A, 0.1)), "pg-ink": toHex(mix(mix(A, B, 0.35), I, 0.15)),
    };
    const tint = (a, i) => toHex(mix(mix(B, A, a), I, i));
    Object.assign(v, { "fan": toHex(mix(P, BLACK, 0.45)), "line-h": tint(0.45, 0.07), "line-h2": tint(0.42, 0.07), "frame": tint(0.1, 0.02),
      "frame-2": tint(0.2, 0.03), "frame-h": tint(0.22, 0.03), "frame-h2": tint(0.32, 0.04), "dot": tint(0.5, 0.25) });
    // اللون المساعد (اختياري): لسطر المؤلف تحت العنوان. الافتراضي مشتق من اللون المميز، ويُضمن وضوحه على الأساسي
    let H = hexOk(t.highlight) ? toRgb(t.highlight) : mix(A, WHITE, 0.25);
    for (let k = 0; k < 20 && contrast(H, P) < 4.5; k++) H = mix(H, WHITE, 0.12);
    v.highlight = toHex(H);
    const enc = encodeURIComponent(v.accent);
    v.pat = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='84' height='84' viewBox='0 0 84 84'%3E%3Cg fill='none' stroke='${enc}' stroke-width='.7' stroke-opacity='.22'%3E%3Cpath d='M42 18l7 17 17 7-17 7-7 17-7-17-17-7 17-7z'/%3E%3Crect x='27' y='27' width='30' height='30' transform='rotate(45 42 42)'/%3E%3Ccircle cx='42' cy='42' r='5'/%3E%3Cpath d='M0 0l12 12M84 0L72 12M0 84l12-12M84 84L72 72'/%3E%3C/g%3E%3C/svg%3E")`;
    return v;
  }
  function themeCss(theme) {
    if (!theme || typeof theme !== "object") return "";
    const t = theme.preset && PRESETS[theme.preset] ? Object.assign({}, PRESETS[theme.preset], theme) : theme;
    if (!["primary", "accent", "bg", "ink"].some((k) => hexOk(t[k]))) return "";
    const v = deriveTheme(t);
    return ":root:root{" + Object.keys(v).map((k) => `--t-${k}:${v[k]}`).join(";") + "}";
  }
  const THEME_KEY = "lib-theme:" + location.pathname.replace(/[^/]*$/, "");
  function applyTheme(theme, opts) {
    const css = themeCss(theme);
    let el = document.getElementById("lib-theme");
    if (!css) { if (el) el.remove(); }
    else {
      if (!el) { el = document.createElement("style"); el.id = "lib-theme"; document.head.appendChild(el); }
      if (el.textContent !== css) el.textContent = css;
    }
    // لون شريط المتصفح والأيقونة
    const cs = getComputedStyle(document.documentElement);
    const prim = cs.getPropertyValue("--t-primary").trim(), acc = cs.getPropertyValue("--t-accent").trim(), bg = cs.getPropertyValue("--t-bg").trim();
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta && css) meta.content = document.body && document.body.classList.contains("reader") ? cs.getPropertyValue("--t-stage").trim() : prim;
    if (css) {
      const ic = document.querySelector('link[rel="icon"]');
      if (ic) ic.href = "data:image/svg+xml," + encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='${prim}'/><path d='M10 22c8-3.5 15-2.5 22 2.5v27c-7-5-14-6-22-2.5z M54 22c-8-3.5-15-2.5-22 2.5v27c7-5 14-6 22-2.5z' fill='${acc}'/><path d='M32 7l2.4 4.9 5.4.8-3.9 3.8.9 5.4L32 19.4l-4.8 2.5.9-5.4-3.9-3.8 5.4-.8z' fill='${bg}'/></svg>`);
    }
    if (!(opts && opts.preview)) { if (css) store.set(THEME_KEY, css); else store.del(THEME_KEY); }
    return css;
  }

  const ar = (n) => Number(n).toLocaleString("ar-SA");

  // ===== العدادات (GoatCounter) — إن تعطلت الخدمة يعمل الموقع عادياً وتختفي الأرقام فقط =====
  const isLocal = () => /^(localhost|127\.|0\.0\.0\.0|\[::1\])/.test(location.hostname) || location.protocol === "file:";
  const en = (n) => Number(n).toLocaleString("en-US");
  function gcBase(code) {
    code = (code || "").trim();
    if (!code) return "";
    if (/^https?:\/\//.test(code)) return code.replace(/\/+$/, "");
    return "https://" + code + ".goatcounter.com";
  }
  // تسجيل زيارة لمسار معيّن — عبر سكربت GoatCounter الرسمي، مع بديل احتياطي
  let gcLoading = null;
  function loadGC(base) {
    if (window.goatcounter && window.goatcounter.count) return Promise.resolve(window.goatcounter);
    if (gcLoading) return gcLoading;
    window.goatcounter = Object.assign(window.goatcounter || {}, { no_onload: true });
    gcLoading = new Promise((ok, no) => {
      const sc = document.createElement("script");
      sc.async = true; sc.src = "https://gc.zgo.at/count.js";
      sc.setAttribute("data-goatcounter", base + "/count");
      sc.setAttribute("data-goatcounter-settings", JSON.stringify({ no_onload: true }));
      sc.onload = () => (window.goatcounter && window.goatcounter.count ? ok(window.goatcounter) : no());
      sc.onerror = no;
      document.head.appendChild(sc);
      setTimeout(no, 8000);
    });
    return gcLoading;
  }
  function track(code, path, title) {
    const base = gcBase(code); if (!base || isLocal()) return;
    loadGC(base).then((gc) => gc.count({ path, title: title || document.title, event: false }))
      .catch(() => {
        try {
          const q = new URLSearchParams({ p: path, t: title || document.title, r: document.referrer || "", s: String(screen.width || ""), rnd: Math.random().toString(36).slice(2) });
          new Image().src = base + "/count?" + q.toString();
        } catch (e) {}
      });
  }
  // قراءة العدد العام لمسار (أو TOTAL لكل الموقع)
  async function hits(code, path, from) {
    const base = gcBase(code); if (!base) return null;
    try {
      // نحدد فترة زمنية (من بداية المكتبة إلى الغد) لأن الرابط بدونها يُرجع نسخة مؤقتة قديمة
      const end = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
      const url = base + "/counter/" + (path === "TOTAL" ? "TOTAL" : encodeURIComponent(path)) + ".json";
      // تاريخ البداية يتغيّر كل 10 دقائق (قبل إنشاء المكتبة دائماً) فلا يُرجع GoatCounter نسخة محفوظة قديمة
      const slot = Math.floor(Date.now() / 600000) % 700;
      const start = new Date(Date.UTC(2026, 0, 1) - slot * 86400000).toISOString().slice(0, 10);
      let q = "?start=" + start + "&end=" + end;
      // فترة محددة (مثل آخر 28 يوماً): نغيّر تاريخ النهاية المستقبلي كل 10 دقائق لنفس السبب
      if (from) q = "?start=" + from + "&end=" + new Date(Date.now() + (1 + slot) * 86400000).toISOString().slice(0, 10);
      let r = await fetch(url + q, { cache: "no-store" });
      if (!r.ok && r.status !== 404) r = await fetch(url + "?start=" + (from || "2026-01-01"), { cache: "no-store" });
      if (r.status === 404) return 0;
      if (!r.ok) return null;
      const j = await r.json();
      const n = parseInt(String(j.count ?? "").replace(/[^0-9]/g, ""), 10);
      return isNaN(n) ? null : n;
    } catch (e) { return null; }
  }
  const bookPath = (b) => "/book/" + (b.id || (b.file || "").replace(/^books\//, "").replace(/\.pdf$/i, ""));

  window.Lib = { applyTheme, themeCss, deriveTheme, PRESETS, repoInfo, loadLibrary, readerUrl, store, ar, titleFromFile, en, track, hits, bookPath };
})();
