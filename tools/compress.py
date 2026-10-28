# ضغط بدون أي تغيير في المحتوى: حذف XMP + تقليص الخطوط المضمّنة لما يُستخدم فقط + ضغط هيكل الملف، ثم تحقق بكسل ببكسل ومطابقة النص
import pymupdf, os, sys, numpy as np
src, dst = sys.argv[1], sys.argv[2]
d = pymupdf.open(src)
d.scrub(metadata=False, xml_metadata=True, attached_files=False, embedded_files=False, thumbnails=True, reset_fields=False, reset_responses=False, clean_pages=False, hidden_text=False, javascript=False, redactions=False, remove_links=False)
d.subset_fonts()
d.save(dst, garbage=4, deflate=True, deflate_fonts=True, deflate_images=True, use_objstms=1, clean=False)
a = pymupdf.open(src); b = pymupdf.open(dst); worst = 0; bad = []
assert a.page_count == b.page_count
for i in range(a.page_count):
    pa = a[i].get_pixmap(dpi=96); pb = b[i].get_pixmap(dpi=96)
    A = np.frombuffer(pa.samples, np.uint8).astype(int); B = np.frombuffer(pb.samples, np.uint8).astype(int)
    w = int(np.abs(A - B).max()) if A.shape == B.shape else 999
    if w: bad.append(i + 1)
    worst = max(worst, w)
ta = "".join(p.get_text() for p in a); tb = "".join(p.get_text() for p in b)
print(f"{os.path.basename(src)} pages={a.page_count} {os.path.getsize(src)/1e6:.1f}MB -> {os.path.getsize(dst)/1e6:.2f}MB maxPixelDiff={worst} badPages={bad[:10]} textSame={ta==tb}", flush=True)
