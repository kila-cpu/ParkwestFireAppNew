# Parkwest Fire Protection — Installer Guide

Interactive demo of the **Installer Guide** for **Parkwest Fire Protection**, prepared by
DMC Consultancy Ltd. It started as a copy of the trial at
`parkwest-installer-guide-production.up.railway.app`. The install register has been taken out
and a desktop layout added.

**Library:** the old 112-drawing library has been replaced by the **six Protecta installation
guides** that Parkwest supplied (EX Mortar, FR Acrylic, FR Board, FR Collar, FR Graphite and
FR Pipe Wrap). Together they hold **1,181 tested details**.

`public/index.html` plus `library.json`, `logo.png`, `drawings/*.webp` (one crop per detail)
and `guides/*.pdf` (the original guides). No build step, no dependencies, no server-side API.

## How the library is built

`tools/extract.py` and `tools/build_library.py` (Python 3 + PyMuPDF + Pillow) read the PDFs.

1. **Extract:** each detail panel is found by its black title bar. The script crops it as an
   image and keeps its callout text, construction line, reference code and page.
2. **Parse:** the text is turned into searchable fields:
   - wall / floor and construction type (drywall, rigid, timber, sandwich panel; concrete, timber, joisted or composite floors), plus minimum thickness
   - service type and plastic material or brand
   - EI / E rating and pipe-end configuration
   - maximum or exact pipe size
   - maximum aperture, joint width or annular gap
   - required pipe insulation (none, local stone wool, or continuous with type and thickness)
3. **Tables:** the 142 size/rating tables are read row by row, including the C/C, U/C, C/U
   and U/U matrices. This lets the app pick the exact row for the pipe.
4. **General instructions:** each guide's numbered general steps and its rules (supporting
   constructions, separations) are taken from page 1.

Re-run after a guide update (output goes to the folder given):

```
python3 tools/extract.py OUT render && python3 tools/build_library.py OUT
```

The values are read automatically, so the app always shows the drawing, the original callout
wording and the guide page, and the installer checks against those.

## The flow

Scan and Find are one 5-step process, with a step bar across the top. Steps 1–2 sit under
the **Scan** tab and steps 3–5 under **Find**.

| # | Step | What works |
| --- | --- | --- |
| 1 | **Photo** | Phone: *Take a photo* (camera) or *Choose from photos*. Desktop: upload or drag a photo in. **Optional** on both, via *Skip — enter details by hand* (the step bar then shows steps 1–2 as skipped) |
| 2 | **Read** | Shows the photo and *What the guide can see*: each field it found, plus anything “Not visible — add in step 3”. **Demo:** the reading is one of four samples, not taken from the photo |
| 3 | **Details** | Every field on one form. Values from the photo are amber (“From photo — check”). **Required:** wall or floor, wall / floor type, thickness, service type (12 types), fire rating and opening size (W × H, or joint width for linear seals), plus the diameter for pipes / cables / conduits, the plastic type for plastic pipe and the brand for composite pipe. *Insulation already on the pipe* is optional; *Not sure* shows every option. There's also an optional typed description (“54 copper, Armaflex, 100 stud wall, 60 min, 150x150 hole”) that fills the boxes on the device, without AI. *Find details* stays blocked until everything required is filled in: it outlines the missing fields in red and scrolls to the first one |
| 4 | **Matches** | Every tested detail across the six guides that fits, closest rating first, with a filter by product. Each card shows the product, the **insulation needed**, rating / pipe ends, construction, size and opening rule, the guide page, and anything the installer must check by eye (e.g. “Check gap”). If nothing fits it says so, links the near misses (reference only) and offers *Change the details* |
| 5 | **Install** | The full installation pack, not just the drawing: your penetration, an **Insulation** callout (what's needed, how much, and whether what's on the pipe will do), **What needs to be done** (numbered steps to tick off, with a progress bar, built from the drawing's callouts, e.g. check service, use the right table row, insulation, backing / shutter, board / mortar / collar / wrap / graphite, coat and fix, seal, pipe ends, final check), **What you'll need** (board m², mortar litres, wraps, collars, stone wool, fixings, sealant), the size table with your row highlighted, the drawing's own wording, the guide's general instructions, and the drawing with a link to the PDF page |

**Library:** one card per Protecta guide (with its general instructions and the original PDF),
search across all 1,181 details, and filters by guide and service. Opening a detail shows the
same full pack, without your penetration.

## Removed from the trial

- **Installs** tab and install register (saving installs, CSV export)
- *Log this install*, *Send to office with photos* and *Report a problem* buttons

## Layout

- **Phone (< 900 px):** bottom tab bar, single column, same as the trial.
- **Desktop (≥ 900 px):** tabs in the header. The step 3 form is 2 columns, matches show as a grid,
  and the install pack has the method beside a sticky drawing.

## Run

```
npm start        # node server.js, port $PORT (default 3000)
```

Deploys to Railway as-is (`railway.json`, health check `/healthz`).
