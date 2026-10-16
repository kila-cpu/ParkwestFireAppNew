# Turn raw panels (extract.py) into a structured library.json the app can match against.
import fitz, json, re, os, sys
from collections import Counter

SP = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.expanduser("~/Downloads/wetransfer_protecta-installation-instructions_2026-10-15_1046")
OUT = sys.argv[1]
P = json.load(open(os.path.join(OUT, "panels.json")))
FILES = {
  "ex-mortar": ("EX-Mortar-Installation-Instructions (3).pdf", "Protecta EX Mortar", "EX Mortar", "Fire-stopping mortar for larger openings in rigid walls and floors."),
  "fr-acrylic": ("FR-Acrylic-Installation-Instructions (3).pdf", "Protecta FR Acrylic", "FR Acrylic", "Intumescent acrylic sealant for small gaps, joints and service penetrations."),
  "fr-board": ("FR-Board-Installation-Instructions (5).pdf", "Protecta FR Board", "FR Board", "Coated stone wool batt for larger openings and mixed services in walls and floors."),
  "fr-collar": ("FR-Collar-Installation-Instructions (1).pdf", "Protecta FR Collar", "FR Collar", "Intumescent collar for plastic pipes, fixed to the face of the wall or the soffit."),
  "fr-graphite": ("FR-Graphite-Installation-Instructions (1).pdf", "Protecta FR Graphite", "FR Graphite", "Graphite intumescent sealant for pipes and tight annular gaps."),
  "fr-pipe-wrap": ("FR-Pipe-Wrap-Installation-Instructions (1).pdf", "Protecta FR Pipe Wrap", "FR Pipe Wrap", "Graphite wrap for plastic pipes and pipes with combustible insulation."),
}
num = lambda s: float(s.replace(",", "."))
def n(s):
    v = num(s); return int(v) if v == int(v) else v

# ---------- guides: general instructions from page 1 ----------
guides = []
for key, (fn, name, short, blurb) in FILES.items():
    doc = fitz.open(os.path.join(SRC, fn))
    t = doc[0].get_text()
    t = t.replace("­", "")
    body = t.split("www.protecta.eu")[0]
    # numbered steps "1.\n text"
    steps, cur, want = [], None, 1
    for line in t.split("\n"):
        m = re.match(r"^\s*(\d{1,2})\.\s*(.*)$", line)
        if m and int(m.group(1)) == want:
            if cur is not None: steps.append(cur)
            cur, want = m.group(2), want + 1; continue
        if cur is not None:
            if re.match(r"^\s*(INSTALLATION|GENERAL GUIDE|CONTENT|INDEX)", line): break
            cur += " " + line
    if cur: steps.append(cur)
    steps = [re.sub(r"\s+", " ", x).strip() for x in steps]
    rules = []
    for lab in ["Minimum separations and limitations", "Supporting constructions", "Services", "Cable support", "Pipe support", "Supports"]:
        m = re.search(re.escape(lab) + r":\s*(.+?)(?=\n[A-Z][A-Za-z ]{3,40}:|\n\s*1\.\s*\n)", t, re.S)
        if m: rules.append({"k": lab, "t": re.sub(r"\s+", " ", m.group(1)).strip()})
    intro = re.search(r"(Protecta®\s+[A-Z][\w ]+?\s+(?:is|are)\s[\s\S]+?)(?=\n\s*Minimum separations|\n\s*Supporting constructions|\n\s*Please refer)", t)
    eta = re.search(r"Installation Instructions to\s*\n?([^\n]+)", t)
    guides.append({"key": key, "name": name, "short": short, "blurb": blurb, "file": f"guides/{key}.pdf", "pages": doc.page_count,
                   "eta": eta.group(1).strip() if eta else "", "intro": re.sub(r"\s+", " ", intro.group(1)).strip() if intro else "",
                   "rules": rules, "steps": steps})

# ---------- per-detail parsing ----------
def kinds_of(title):
    t = title.upper(); k = []
    if "LINEAR" in t or re.search(r"\b(HORIZONTAL|VERTICAL)\b.*SEALS", t): k.append("linear")
    if "EMPTY HOLE" in t: k.append("empty")
    if "BUS-BAR" in t: k.append("busbar")
    if "UNISTRUT" in t: k.append("unistrut")
    if "TRUNKING" in t or "DUCT" in t: k.append("trunking")
    if re.search(r"\bCABLE|CONDUCTORS AND CABLE", t): k.append("cables")
    if "CONDUIT" in t: k.append("conduit")
    if re.search(r"\bPEX PIPE", t): k.append("pex")
    elif "ALUPEX" in t or "AQUATECHNIK" in t: k.append("alupex")
    if "COPPER" in t or "METAL PIPES" in t: k.append("copper")
    if re.search(r"\bSTEEL\b|GAS PIPE|METAL PIPES", t): k.append("steel")
    if re.search(r"\b(PVC|PE|PP|ABS|PLASTIC|POLYBUTYLENE|COMPOSITE|LK PAL)\b", t) and "CONDUIT" not in t.replace("PIPES & CONDUITS", "") and "DUCT" not in t: k.append("plastic")
    if "PIPES & CONDUITS" in t and "plastic" not in k: k.append("plastic")
    return sorted(set(k))

BRANDS = ["Aquatherm Green SDR9", "BluePower", "Geberit Silent-PP", "Huliot Ultra Silent", "Polo-Kal NG", "Rehau Raupiano Plus", "Uponor Decibel", "Valsir Blackfire", "Valsir PP3", "Valsir Triplus", "Wavin AS+", "Wavin SiTech", "LK PAL Universal"]
def mats_of(text):
    t = text.upper(); m = set()
    if re.search(r"\bPVC", t.replace("SAN+PVC", "SAN")): m.add("PVC")
    if re.search(r"\b(PE|ABS|SAN|HDPE|PE-HD)\b", t) and "PEX" not in t: m.add("PE")
    if re.search(r"\bPP\b|POLYPROPYLENE|PP-", t): m.add("PP")
    if "POLYBUTYLENE" in t or re.search(r"\bPB\b", t): m.add("PB")
    for b in BRANDS:
        if b.upper().replace(" ", "") in t.replace(" ", "").replace("-", "-"): m.add(b)
    if "COMPOSITE" in t: m.add("Composite")
    return m

def construction(cons):
    c = cons.upper(); walls, floors = [], []
    thk = re.search(r"≥\s*(\d+)\s*MM", c)
    if "WALL" in c:
        if re.search(r"DRYWALL|FLEXIBLE(?: OR RIGID)? WALL|FLEXIBLE WALLS", c): walls.append("Drywall")
        if re.search(r"RIGID|MASONRY|CONCRETE", c) and ("WALL" in c.split("RIGID")[-1] or "MASONRY" in c or re.search(r"RIGID WALL|RIGIDS", c)): walls.append("Rigid")
        if "TIMBER WALL" in c: walls.append("Timber")
        if "PANEL WALL" in c: walls.append("Panel")
        if "RIGIDS" in c and "Rigid" not in walls: walls.append("Rigid")
    if "FLOOR" in c:
        if re.search(r"RIGID FLOOR|TIMBER & RIGID|RIGID WALLS? AND FLOORS|BETWEEN FLOORS|RIGID FLOORS", c) or re.search(r"IN ≥ ?\d+MM RIGID FLOORS", c): floors.append("Rigid")
        if "TIMBER" in c and "FLOOR" in c and "TIMBER WALL" not in c: floors.append("Timber")
        if "FLEXIBLE FLOOR" in c: floors.append("Flexible")
        if "COMPOSITE FLOOR" in c: floors.append("Composite")
        if "BETWEEN" in c and "WALLS AND FLOORS" in c and not floors: floors.append("Rigid")
    if not walls and "WALL" in c and "RIGID" in c: walls.append("Rigid")
    return {"walls": sorted(set(walls)), "floors": sorted(set(floors)), "minThk": int(thk.group(1)) if thk else None,
            "joint": "BETWEEN" in c, "substrate": re.search(r"AND (STEEL|ALUMINIUM|GYPSUM) SUBSTRATES", c).group(1).title() if re.search(r"AND (STEEL|ALUMINIUM|GYPSUM) SUBSTRATES", c) else None}

def rating(text):
    t = text.upper()
    ei = re.search(r"\bEI\s*(\d+)(?:\s*[-–]\s*(\d+))?", t)
    e = re.search(r"\(E\s*(\d+)", t) or re.search(r"(?<![A-Z])E\s*(\d+)", t.replace("EI", "XX"))
    ends = re.search(r"\b([CU]/[CU])\b", t)
    return {"ei": int(ei.group(2) or ei.group(1)) if ei else None, "eiMin": int(ei.group(1)) if ei else None,
            "e": int(e.group(1)) if e else None, "ends": ends.group(1) if ends else None}

def apertures(blocks):
    out, seal = [], None
    for b in blocks:
        t = b.replace(" ", " ")
        for m in re.finditer(r"Maximum\s+(\d+)\s*mm\s+wide\s+(?:\w+\s+)?joints()", t, re.I):
            seal = max(seal or 0, int(m.group(1)))
        for m in re.finditer(r"(?:Maximum\s+)?(?:seal|joint)\s+width\s*(?:of\s*)?(\d+)(?:\s*[-–]\s*(\d+))?\s*mm", t, re.I):
            v = int(m.group(2) or m.group(1)); seal = max(seal or 0, v)
        if not re.search(r"aperture|opening", t, re.I) or re.search(r"oversail|sealed with|into aperture|Framed aperture", t, re.I) and not re.search(r"Maximum aperture", t, re.I): continue
        seg = t[re.search(r"aperture|opening", t, re.I).start():]
        for m in re.finditer(r"unlimited width by (\d+)\s*mm high", seg, re.I): out.append({"w": "unlimited", "h": int(m.group(1))})
        for m in re.finditer(r"(\d+)\s*mm wide (?:by|and|x)\s*(\d+)\s*mm high", seg, re.I): out.append({"w": int(m.group(1)), "h": int(m.group(2))})
        for m in re.finditer(r"(\d+)\s*mm high (?:by|and|x)\s*(\d+)\s*mm wide", seg, re.I): out.append({"w": int(m.group(2)), "h": int(m.group(1))})
        for m in re.finditer(r"(?<![\d.])(\d+(?:[.,]\d+)?)\s*(m|mm)?\s*(?:x|×|by)\s*(\d+(?:[.,]\d+)?)\s*(mm|m)\b(?!\s*(?:high|wide))", seg, re.I):
            u = (m.group(2) or m.group(4)).lower(); f = 1000 if u == "m" else 1
            a, b2 = num(m.group(1)) * f, num(m.group(3)) * f
            if a >= 20 and b2 >= 20: out.append({"w": int(a), "h": int(b2), "any": True})
        for m in re.finditer(r"aperture\s*(?:of\s*)?Ø\s*(\d+)\s*mm|or\s*Ø\s*(\d+)\s*mm", seg, re.I): out.append({"dia": int(m.group(1) or m.group(2))})
        if re.search(r"Aperture ≤ collar|annular gap", t, re.I) and not out: out.append({"note": re.sub(r"\s+", " ", t)})
    # drop soffit-only duplicates (550 high by 1100 wide) — they are extra, keep but mark
    seen, uniq = set(), []
    for a in out:
        k = json.dumps(a, sort_keys=True)
        if k not in seen: seen.add(k); uniq.append(a)
    return uniq, seal

def rect_size(blocks):
    for b in blocks:
        m = re.search(r"(trunking|duct|bus-?bars?|channel)[^≤]*≤\s*(\d+)\s*(?:mm)?\s*[x×]\s*(\d+)\s*mm", b, re.I)
        if m: return [int(m.group(2)), int(m.group(3))]
    return None

def gaps(blocks):
    mx, has_min, txt = None, False, []
    for b in blocks:
        hit = False
        for rx in [r"annular (?:ring|gap)(?: width)?\s*(?:of\s*)?(?:≤\s*)?(\d+)\s*mm", r"≤\s*(\d+)\s*mm\s*(?:annular\s*)?gaps?\b", r"gap around the \w+ of ≤\s*(\d+)\s*mm", r"gaps? (?:of|up to)\s*≤?\s*(\d+)\s*mm"]:
            for m in re.finditer(rx, b, re.I):
                if re.search(r"Maximum annular|≤|gap around|up to", m.group(0), re.I) or "annular" in m.group(0).lower():
                    mx = max(mx or 0, int(m.group(1))); hit = True
        if re.search(r"≥\s*\d+\s*mm\s*(?:annular\s*)?gaps?", b, re.I) and not re.search(r"maximum aperture", b, re.I): has_min = True; hit = True
        if hit: txt.append(b)
    return (None if has_min else mx), txt

BUNDLE = [None]
def sizes(blocks, kinds):
    BUNDLE[0] = None
    mx, mn, exact, upto = None, None, [], False
    for b in blocks:
        if re.search(r"aperture|annular gap|collar diamet", b, re.I) and not re.search(r"pipe|cable|conduit", b.split("aperture")[0], re.I): continue
        if re.search(r"FR Collar|screws|Pipe Wraps?\b", b, re.I): continue
        for m in re.finditer(r"(≤|≥)?\s*Ø\s*(\d+(?:[.,]\d+)?)\s*(?:[-–]\s*(\d+(?:[.,]\d+)?))?\s*mm", b):
            pre = b[max(0, m.start() - 25):m.start()]
            if re.search(r"aperture", pre, re.I): continue
            if re.search(r"bundles?\s*(?:of\s*)?$|bundled\s*$", pre, re.I):
                BUNDLE[0] = max(BUNDLE[0] or 0, num(m.group(3) or m.group(2))); continue
            hi = num(m.group(3) or m.group(2))
            mx = max(mx or 0, hi)
            if m.group(1) == "≥": mn = num(m.group(2))
            elif m.group(1) == "≤" or m.group(3): upto = True
            else: exact.append(hi)
    if exact and not upto and not mn and len(set(exact)) == 1: mn = exact[0]
    return (n(str(mx)) if mx else None), (n(str(mn)) if mn else None)

INS_WORDS = [("elastomeric", r"elastomeric|armaflex"), ("pe", r"\bPE foam|PE foam|or PE\b|\bPE insulation"), ("phenolic", r"phenolic"), ("pu", r"\bPU\b|polyurethane"),
             ("stone", r"stone wool|stonewool|rock ?wool|mineral wool"), ("glass", r"glass wool|glass-? or stone|glass or stone")]
def insulation(blocks, title):
    cont, local = [], []
    for b in blocks:
        m = re.search(r"((\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?)\s*mm\s*(?:thick\s*)?continuous.*)", b, re.I)
        seg = m.group(1) if m else (b if re.search(r"continuous", b, re.I) and not re.search(r"backing|shutter|Stone wool depth", b, re.I) else None)
        if seg and re.search(r"insulation|wool|foam", seg, re.I):
            types = [k for k, rx in INS_WORDS if re.search(rx, seg, re.I)]
            seg = re.split(r"\s(?=(?:Copper|Steel|Alupex|PEX|PE|PP|PVC|Plastic|Metal)\b[^.]*\b(?:pipe|pipes)\b)", seg)[0]
            cont.append({"types": types or ["any"], "thk": re.sub(r"\s", "", m.group(2)).replace("–", "-").replace(",", ".") if m else None, "t": seg.strip()})
            continue
        if re.search(r"backing|shutter|Stone wool depth|plugged|to fill|gaps between", b, re.I): continue
        if re.search(r"(stone|glass)[- ]?(?:or stone )?wool", b, re.I) and re.search(r"installed|≥\s*\d+\s*cm|cm (on|from)", b, re.I):
            types = [k for k, rx in INS_WORDS if re.search(rx, b, re.I) and k in ("stone", "glass")]
            thk = re.search(r"≥\s*(\d+)\s*mm", b); ln = re.search(r"≥\s*(\d+)\s*cm", b)
            st = re.search(r"≥\s*\d+\s*mm\s*(?:pipe insulation of\s*)?(?:glass|stone)[\s\S]*", b, re.I)
            local.append({"types": types, "thk": thk.group(1) if thk else None, "len": ln.group(1) if ln else None, "t": (st.group(0) if st else b).strip()})
    if cont: return {"mode": "continuous", "opts": cont}
    if local: return {"mode": "local", "opts": local}
    if "INSULATED" in title.upper(): return {"mode": "unknown"}
    return {"mode": "none"}

def parse_table(doc, p):
    page = doc[p["page"] - 1]
    tabs = page.find_tables(clip=fitz.Rect(p["rect"])).tables
    if not tabs: return None
    rows = [[re.sub(r"\bSe ?r ?v ?ices\b", "Services", (c or "").replace("\n", " ")).strip() for c in r] for r in tabs[0].extract()]
    # find header row
    hi = next((i for i, r in enumerate(rows) if any(re.fullmatch(r"[CU]/[CU]", c) for c in r)), None)
    if hi is None: hi = next((i for i, r in enumerate(rows) if any(re.match(r"^(Classification|Fire Classification)", c) for c in r)), None)
    if hi is None: hi = 0
    head = rows[hi]
    opts, carry = [], ""
    body = [r for r in rows[hi + 1:] if any(r)]
    # drop columns that are empty everywhere (layout artefacts)
    keep = [j for j in range(len(head)) if head[j] or any(j < len(r) and r[j] for r in body)]
    head = [head[j] for j in keep]; body = [[r[j] if j < len(r) else "" for j in keep] for r in body]
    endcols = {j: c for j, c in enumerate(head) if re.fullmatch(r"[CU]/[CU]", c)}
    lab = next((j for j, h in enumerate(head) if re.match(r"(Services?|Pipe)\b(?!.*(Diameter|Wall|Wrap|Insulation))", h, re.I)), 0)
    diacol = next((j for j, h in enumerate(head) if re.search(r"Diamet", h, re.I)), None)
    for ri, r in enumerate(body):
        if r[lab]: carry = r[lab]
        label = r[lab] or carry
        dia = dmin = None
        m = re.search(r"Ø\s*(\d+(?:[.,]\d+)?)\s*(?:[-–]\s*(\d+(?:[.,]\d+)?))?", label) or (re.search(r"Ø\s*(\d+(?:[.,]\d+)?)\s*(?:[-–]\s*(\d+(?:[.,]\d+)?))?", r[diacol]) if diacol is not None else None)
        if not m and diacol is not None: m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)(?:\s*[-–]\s*(\d+(?:[.,]\d+)?))?\s*(?:mm)?", r[diacol])
        if m:
            dia = num(m.group(2) or m.group(1)); dmin = num(m.group(1)) if m.group(2) else None
            src = label if "Ø" in label else (r[diacol] if diacol is not None else "")
            if not m.group(2) and "Ø" in src and not re.search(r"≤\s*Ø", src): dmin = dia   # "Ø160mm" means exactly 160
        extra = [(f"{head[j]}: " if head[j] else "") + c for j, c in enumerate(r) if j not in endcols and j != lab and c and c != "-" and not re.search(r"\bEI\s*\d|^\(E", c)]
        mats = sorted(mats_of(label + " " + p["title"]))
        cells = [(ends, r[j]) for j, ends in endcols.items()] if endcols else [(None, next((c for c in r if re.search(r"\bEI\s*\d", c)), ""))]
        for ends, c in cells:
            rr = rating(c)
            if rr["ei"]: opts.append({"label": label, "mats": mats, "dia": n(str(dia)) if dia else None, "dmin": n(str(dmin)) if dmin else None, "extra": extra, "ei": rr["ei"], "e": rr["e"], "ends": ends or rr["ends"], "ri": ri})
    return {"head": head, "rows": body, "opts": opts}

docs = {k: fitz.open(os.path.join(SRC, v[0])) for k, v in FILES.items()}
details = []
for p in P:
    blocks = [b["t"] for b in sorted(p["blocks"], key=lambda b: (b["y"], b["x"]))]
    code = next((b for b in blocks if re.fullmatch(r"\d{2}/\d{4}-[A-Z][\w.\-]*", b.strip())), None)
    table = parse_table(docs[p["guide"]], p) if p["full"] else None
    if table and not table["opts"]: table = None
    callouts = [b for b in blocks if b != code]
    if table:  # drop the table's own text from the callouts
        cells = set(c for r in table["rows"] + [table["head"]] for c in r if c)
        callouts = [b for b in callouts if not any(c in b for c in cells if len(c) > 6) or re.search(r"Protecta|sealed|stone wool|aperture|Maximum", b)]
        callouts = [b for b in callouts if not re.match(r"^(Services|Pipe Wall|Pipe Wrap|Classification|Pipe & Collar|Fire Classifications|Composite Plastic Pipes)\b", b)]
    callouts = [b for b in callouts if not re.fullmatch(r"(Services|Pipe Wall Thickness|Pipe Wrap|Classification|Pipe|Service insulation|Pipe Diameter|Minimum Collar(?: Height)?)", b)]
    callouts = [b for b in callouts if not re.search(r"\[mm\]|C/C U/C|^Height\b", b)]
    callouts = list(dict.fromkeys(callouts))
    con = construction(p["cons"])
    kinds = kinds_of(p["title"])
    rt = rating(p["title"])
    aps, seal = apertures(callouts)
    mx, mn = sizes(callouts, kinds); bundle = BUNDLE[0]
    d = {"id": p["id"], "guide": p["guide"], "page": p["page"], "code": code, "title": p["title"].strip(), "cons": p["cons"].strip(),
         "surfaces": [s for s, ok in (("Wall", bool(con["walls"])), ("Floor", bool(con["floors"]))) if ok],
         "walls": con["walls"], "floors": con["floors"], "minThk": con["minThk"], "joint": con["joint"], "substrate": con["substrate"],
         "kinds": kinds, "mats": sorted(mats_of(p["title"])) if "plastic" in kinds or "conduit" in kinds else [],
         "ei": rt["ei"], "eiMin": rt["eiMin"], "e": rt["e"], "ends": rt["ends"],
         "maxDia": mx, "minDia": mn, "aps": aps, "sealW": seal, "gapMax": gaps(callouts)[0], "svcRect": rect_size(callouts), "bundleMax": None,
         "ins": insulation(callouts, p["title"]) if set(kinds) & {"copper", "steel", "alupex", "plastic", "pex"} else {"mode": "na"},
         "callouts": callouts}
    if bundle: d["bundleMax"] = n(str(bundle))
    if d["maxDia"] is None and bundle: d["maxDia"] = n(str(bundle))
    if "trunking" in kinds and not d["mats"]: d["mats"] = sorted(mats_of(" ".join(callouts)))
    if "plastic" in kinds and not [m for m in d["mats"] if m != "Composite"]:
        d["mats"] = sorted(set(d["mats"]) | set().union(*[mats_of(c) for c in callouts if re.search(r"pipe", c, re.I) and not re.search(r"Collar|Wrap", c)] or [set()]))
    if table:
        d["table"] = {"head": table["head"], "rows": table["rows"]}; d["opts"] = table["opts"]
        for o in d["opts"]:
            ok = [k for k in kinds_of(o["label"]) if k in ("copper", "steel", "alupex", "pex", "cables", "conduit")]
            if ok: o["kinds"] = ok
        d["kinds"] = sorted(set(d["kinds"]) | set(k for o in d["opts"] for k in o.get("kinds", [])))
        if d["ei"] is None: d["ei"] = max(o["ei"] for o in table["opts"])
        if not d["mats"]: d["mats"] = sorted(set(m for o in table["opts"] for m in o["mats"]))
        dias = [o["dia"] for o in table["opts"] if o["dia"]]
        if dias and not d["maxDia"]: d["maxDia"] = max(dias)
    details.append(d)

json.dump({"generated": "2026-10-16", "source": "Protecta installation instructions (6 guides) supplied by Parkwest", "guides": guides, "details": details},
          open(os.path.join(OUT, "library.json"), "w"), ensure_ascii=False, separators=(",", ":"))

# ---------- coverage report ----------
C = Counter(); NA = []
for d in details:
    C["total"] += 1
    if not d["surfaces"]: C["no surface"] += 1
    if not (d["walls"] or d["floors"]): C["no base"] += 1
    if not d["kinds"]: C["no kind"] += 1; print("NOKIND", d["title"])
    if d["ei"] is None: C["no EI"] += 1
    if not d["aps"] and not d["sealW"] and not d["gapMax"]: C["no aperture"] += 1; NA.append(d)
    if d["minThk"] is None: C["no thk"] += 1
    if d["maxDia"] is None and set(d["kinds"]) & {"copper", "steel", "alupex", "plastic", "pex", "cables", "conduit"}: C["no dia"] += 1
    if d["ins"]["mode"] == "unknown": C["ins unknown"] += 1
    if "table" in d: C["tables"] += 1
print(dict(C))
print(Counter(k for d in details for k in d["kinds"]))
print("guides:", [(g["key"], len(g["steps"]), len(g["rules"]), bool(g["intro"])) for g in guides])
import random; random.seed(5)
for d in random.sample(NA, min(6, len(NA))): print("NOAP", d["id"], d["title"], "|", " / ".join(c[:70] for c in d["callouts"]))
for g in guides: print(g["key"], "|", g["intro"][:110], "|", g["steps"][:1])
