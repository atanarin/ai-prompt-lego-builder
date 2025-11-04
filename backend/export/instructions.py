# backend/export/instructions.py
from typing import List, Dict, Optional, Tuple
import os
from collections import Counter
from PIL import Image, ImageDraw

# ===== Tunables =====
SCALE      = 64        # pixels per stud (crisper; PDF stays sharp)
PLI_COLS   = 2         # how many columns in the parts list panel
PLI_TH     = 56        # per-item thumbnail height (px)
PLI_GAP    = 10        # gap between rows/cols in PLI
PLI_W_COL  = 260       # width per PLI column (thumb+labels)
MARGIN     = 24
GRID_ALPHA = 220
MAX_PAGES  = 300       # safety cap

COLOR_MAP = {
    "red": (220, 60, 60),
    "black": (40, 40, 40),
    "light_gray": (205, 205, 205),
    "white": (255, 255, 255),
    "blue": (60, 90, 200),
    "green": (60, 160, 90),
    "yellow": (230, 200, 60),
}

def _rgb(name: str): 
    return COLOR_MAP.get(name, (180, 180, 180))

def _short(n: str) -> str:
    # short label e.g. "Plate 2x4" -> "2x4"
    return n.split(" ", 1)[1] if " " in n else n

def _canvas(W: int, L: int) -> Tuple[Image.Image, ImageDraw.ImageDraw, int, int, int, int, int]:
    board_w  = L * SCALE
    board_h  = W * SCALE
    pli_w    = PLI_COLS * PLI_W_COL + (PLI_COLS-1)*PLI_GAP
    img_w    = MARGIN + board_w + MARGIN + pli_w + MARGIN
    img_h    = MARGIN + board_h + MARGIN
    img = Image.new("RGB", (img_w, img_h), (245,245,245))
    d = ImageDraw.Draw(img)
    # board area
    gx = MARGIN; gy = MARGIN
    # grid
    grid_color = (220,220,220,GRID_ALPHA)
    for x in range(L+1):
        d.line([(gx + x*SCALE, gy), (gx + x*SCALE, gy + board_h)], fill=grid_color, width=1)
    for y in range(W+1):
        d.line([(gx, gy + y*SCALE), (gx + board_w, gy + y*SCALE)], fill=grid_color, width=1)
    # PLI panel origin
    px = gx + board_w + MARGIN
    py = gy
    # panel rect
    d.rectangle([(px-8, py-8), (px + pli_w + 8, py + board_h + 8)], outline=(205,205,205), width=1, fill=(252,252,252))
    d.text((px, py), "Parts this step", fill=(25,25,25))
    return img, d, gx, gy, px, py, board_h

def _draw_rect_label(d: ImageDraw.ImageDraw, x0,y0,x1,y1, fill, text):
    d.rectangle((x0,y0,x1,y1), fill=fill, outline=(30,30,30))
    if (x1-x0) >= 64 and (y1-y0) >= 24:
        d.text((x0+6, y0+6), text, fill=(0,0,0))

def _count_by_part_color(parts: List[Dict]):
    c = Counter((p["ldraw"], p["color"], _short(p.get("name","")) or p["ldraw"]) for p in parts)
    # sort: by ldraw then color
    return sorted(((ld, col, label, n) for (ld, col, label), n in c.items()), key=lambda t:(t[0], t[1]))

def _stud_color(base):
    # slightly darker circles on top
    return tuple(max(0, int(c*0.7)) for c in base)

def _draw_stud_topdown(d: ImageDraw.ImageDraw, x, y, r, color):
    d.ellipse((x-r, y-r, x+r, y+r), outline=(30,30,30), fill=_stud_color(color))

def _draw_part_thumb_topdown(d: ImageDraw.ImageDraw, box: Tuple[int,int,int,int], color_name: str, l: int, w: int):
    """
    Top-down 2.5D: draw a rectangle l×w studs with stud bumps.
    l = length in studs (X direction), w = width in studs (Y direction)
    """
    x0,y0,x1,y1 = box
    fill = _rgb(color_name)
    # outer
    d.rectangle((x0,y0,x1,y1), fill=fill, outline=(40,40,40))
    # studs grid
    cols = max(1, l)
    rows = max(1, w)
    # leave small margins inside the thumb
    padx = 8; pady = 8
    rw = (x1 - x0 - 2*padx) / cols
    rh = (y1 - y0 - 2*pady) / rows
    r  = int(min(rw, rh) * 0.25)
    for cx in range(cols):
        for cy in range(rows):
            sx = int(x0 + padx + cx*rw + rw/2)
            sy = int(y0 + pady + cy*rh + rh/2)
            _draw_stud_topdown(d, sx, sy, r, fill)

def _pli_cell_rect(px, py, col, row):
    x = px + col*(PLI_W_COL + PLI_GAP)
    y = py + 28 + row*(PLI_TH + PLI_GAP)
    return (x, y, x + PLI_W_COL, y + PLI_TH)

def draw_step_image(placements: List[Dict], step_id: int, W: int, L: int, out_path: str):
    img, d, gx, gy, px, py, board_h = _canvas(W, L)

    # previous steps dimmed
    for p in placements:
        if int(p["step"]) >= step_id:
            continue
        x0 = gx + p["x"]*SCALE; y0 = gy + p["y"]*SCALE
        x1 = gx + (p["x"]+p["l"])*SCALE; y1 = gy + (p["y"]+p["w"])*SCALE
        fill = tuple(int(c*0.35) for c in _rgb(p["color"]))
        _draw_rect_label(d, x0,y0,x1,y1, fill, _short(p.get("name","")))

    # current step
    new_parts = [p for p in placements if int(p["step"]) == step_id]
    for p in new_parts:
        x0 = gx + p["x"]*SCALE; y0 = gy + p["y"]*SCALE
        x1 = gx + (p["x"]+p["l"])*SCALE; y1 = gy + (p["y"]+p["w"])*SCALE
        _draw_rect_label(d, x0,y0,x1,y1, _rgb(p["color"]), _short(p.get("name","")))

    # PLI — multi-column layout inside the same page height
    rows = _count_by_part_color(new_parts)
    if rows:
        # how many rows fit per column?
        rows_per_col = max(1, int((board_h - 36) // (PLI_TH + PLI_GAP)))
        col = row = 0
        for (ldraw, color, label, qty) in rows:
            # break column
            if row >= rows_per_col:
                col += 1; row = 0
            # if PLI overflow columns, we just keep adding columns (visible horizontally);
            # for *very* big steps, reduce batch size in planner.
            cell = _pli_cell_rect(px, py, col, row)
            # thumb rect within cell
            tx0, ty0, tx1, ty1 = (cell[0]+6, cell[1]+4, cell[0]+6+112, cell[1]+4+PLI_TH-8)
            # parse size from label if present (e.g., "2x4")
            l = w = 1
            # prefer placements info later if needed; for now parse l×w if label has it
            if "x" in label:
                parts = label.lower().split("x")
                try:
                    l = max(1, int(parts[0].split()[-1]))
                    w = max(1, int(parts[1].split()[0]))
                except:
                    l, w = 2, 2
            _draw_part_thumb_topdown(d, (tx0,ty0,tx1,ty1), color, l, w)
            # labels
            d.text((tx1+6, ty0+4), f"{ldraw}", fill=(40,40,40))
            d.text((tx1+6, ty0+24), f"{color} ×{qty}", fill=(40,40,40))
            row += 1

    img.save(out_path)  # keep native size; PDF stays crisp

def write_instruction_set(
    placements: List[Dict],
    outdir: str,
    H: int, W: int, L: int,
    spec: Optional[dict] = None,
    pdf_path: Optional[str] = None,
    step_count: Optional[int] = None
):
    steps_dir = os.path.join(outdir, "instructions", "steps")
    os.makedirs(steps_dir, exist_ok=True)

    if step_count is None:
        step_count = 1 + max(int(p.get("step", 0)) for p in placements) if placements else 0

    page_limit = min(step_count, MAX_PAGES)
    placements = sorted(placements, key=lambda p: (int(p["step"]), p["y"], p["x"], p["ldraw"]))

    for s in range(page_limit):
        out_path = os.path.join(steps_dir, f"step_{s:02d}.png")
        draw_step_image(placements, s, W, L, out_path)

    # HTML
    css = """
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;color:#222}
    .btn{display:inline-block;margin-top:12px;padding:10px 14px;border-radius:10px;border:1px solid #ddd;text-decoration:none;color:#111}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(520px,1fr));gap:16px;margin-top:24px}
    .card{border:1px solid #e6e6e6;border-radius:12px;padding:12px}
    img.step{width:100%;height:auto;border-radius:10px;border:1px solid #eee}
    .muted{color:#666}
    """
    html = [ "<html><head><meta charset='utf-8'><title>LEGO Instructions</title>",
             f"<style>{css}</style></head><body>" ]
    html.append("<h1>Build Instructions</h1>")
    if spec:
        html.append(f"<div>Style: <b>{spec.get('style','')}</b> — Size: <b>{spec.get('length_studs','?')}×{spec.get('width_studs','?')}</b> studs — Height: <b>{spec.get('height_layers','?')}</b> layers</div>")
    if pdf_path and os.path.isfile(pdf_path):
        html.append(f"<a class='btn' href='{os.path.relpath(pdf_path, outdir)}' download>Download PDF</a>")
    if page_limit < step_count:
        html.append(f"<div class='muted'>Showing first {page_limit} of {step_count} steps (capped).</div>")
    html.append("<div class='grid'>")
    for s in range(page_limit):
        step_png = os.path.join("instructions", "steps", f"step_{s:02d}.png")
        html.append("<div class='card'>")
        html.append(f"<h3>Step {s}</h3>")
        html.append(f"<img class='step' src='{step_png}' alt='Step {s}'>")
        html.append("</div>")
    html.append("</div></body></html>")
    with open(os.path.join(outdir, "instructions.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(html))
