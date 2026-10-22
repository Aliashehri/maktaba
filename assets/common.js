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

  const ar = (n) => Number(n).toLocaleString("ar-SA");

  window.Lib = { repoInfo, loadLibrary, readerUrl, store, ar, titleFromFile };
})();
