# Pull every detail panel out of the 6 Protecta guides: crop image + raw text.
import fitz, json, re, sys, os
SRC = os.path.expanduser("~/Downloads/wetransfer_protecta-installation-instructions_2026-10-15_1046")
GUIDES = [
  ("ex-mortar", "Protecta EX Mortar", "EX-Mortar-Installation-Instructions (3).pdf"),
  ("fr-acrylic", "Protecta FR Acrylic", "FR-Acrylic-Installation-Instructions (3).pdf"),
  ("fr-board", "Protecta FR Board", "FR-Board-Installation-Instructions (5).pdf"),
  ("fr-collar", "Protecta FR Collar", "FR-Collar-Installation-Instructions (1).pdf"),
  ("fr-graphite", "Protecta FR Graphite", "FR-Graphite-Installation-Instructions (1).pdf"),
  ("fr-pipe-wrap", "Protecta FR Pipe Wrap", "FR-Pipe-Wrap-Installation-Instructions (1).pdf"),
]
OUT = sys.argv[1]
RENDER = len(sys.argv) > 2 and sys.argv[2] == "render"
os.makedirs(OUT + "/drawings", exist_ok=True)

def dark(c): return c is not None and all(v < 0.25 for v in c)

panels = []
for key, name, fn in GUIDES:
    doc = fitz.open(os.path.join(SRC, fn))
    for pno, page in enumerate(doc):
        H = page.rect.height
        bars = []
        for dr in page.get_drawings():
            r = dr["rect"]
            if dark(dr.get("fill")) and r.width > 120 and 8 < r.height < 22 and 50 < r.y0 < H - 90:
                # must carry white text
                txt = "".join(s["text"] for b in page.get_text("dict", clip=r)["blocks"] for l in b.get("lines", []) for s in l["spans"] if s["color"] > 0xE0E0E0).strip()
                if txt: bars.append((r, txt))
        bars.sort(key=lambda b: (round(b[0].y0), b[0].x0))
        # dedupe overlapping bars
        uniq = []
        for r, t in bars:
            if not any(abs(r.y0 - u[0].y0) < 3 and abs(r.x0 - u[0].x0) < 3 for u in uniq): uniq.append((r, t))
        bars = uniq
        if not bars: continue
        # bottom of content: the orange footer begins around H-70
        footer = H - 72
        for dr in page.get_drawings():
            r = dr["rect"]; f = dr.get("fill")
            if f and f[0] > 0.8 and f[1] < 0.6 and r.width > 400 and r.y0 > H * 0.7: footer = min(footer, r.y0)
        for i, (r, t) in enumerate(bars):
            below = [b[0] for b in bars if b[0].y0 > r.y1 + 5 and b[0].x0 < r.x1 - 20 and b[0].x1 > r.x0 + 20]
            y1 = (min(b.y0 for b in below) - 4) if below else footer - 4
            rect = fitz.Rect(r.x0 - 3, r.y0 - 2, r.x1 + 3, y1)
            # text inside, by block
            blocks, cons = [], []
            for b in page.get_text("dict", clip=rect)["blocks"]:
                lines = []
                for l in b.get("lines", []):
                    lb = fitz.Rect(l["bbox"])
                    if lb.intersects(r) and lb.y1 <= r.y1 + 2: continue  # the title bar text
                    s = "".join(sp["text"] for sp in l["spans"]).strip()
                    if not s: continue
                    if lb.y0 < r.y1 + 30 and re.search(r"(WALL|FLOOR|SLAB|PARTITION|SHAFT)", s) and s.upper() == s:
                        cons.append(s); continue
                    lines.append(s)
                if lines:
                    bb = b["bbox"]
                    blocks.append({"t": re.sub(r"\s+", " ", " ".join(lines)), "y": round(bb[1]), "x": round(bb[0])})
            pid = f"{key}-p{pno+1}-{i+1}"
            if RENDER:
                pix = page.get_pixmap(clip=rect, dpi=int(os.environ.get("DPI", "130")))
                from PIL import Image
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                im.save(f"{OUT}/drawings/{pid}.webp", "WEBP", quality=int(os.environ.get("Q", "62")), method=6)
            panels.append({"id": pid, "guide": key, "guideName": name, "page": pno + 1, "title": re.sub(r"\s+", " ", t),
                           "rect": [round(v) for v in rect], "full": rect.width > 400, "cons": " ".join(cons), "blocks": blocks})
json.dump(panels, open(OUT + "/panels.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(len(panels), Counter(p["guide"] for p in panels))
