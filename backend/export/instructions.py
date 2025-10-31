# backend/export/instructions.py
from typing import List, Dict, Optional, Tuple
import os
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

# === Tunables ===
SCALE = 36         # pixels per stud (crisp but faster than 48)
PLI_W = 420        # width of the parts list panel (px)
MARGIN = 24        # outer margins around canvas (px)
MAX_PAGES = 200    # safety cap for very large models

COLOR_MAP = {
    "red": (220, 60, 60),
    "black": (40, 40, 40),
    "light_gray": (200, 200, 200),
    "white": (255, 255, 255),
    "blue": (60, 90, 200),
    "green": (60, 160, 90),
    "yellow": (230, 200, 60),
}

def _rgb(name: str): 
    return COLOR_MAP.get(name, (180, 180, 180))

def _part_thumb_box(idx: int, xoff: int, y0: int, thumb_h: int = 42) -> Tuple[int,int,int,int]:
    pad = 8
    top = y0 + idx*(thumb_h + pad)
    return (xoff + 12, top, xoff + 12 + 64, top + thumb_h)

def _draw_part_thumb(d: ImageDraw.ImageDraw, box: Tuple[int,int,int,int], ldraw: str, color: str):
    # simple silhouettes so PLI is visible in PNG/PDF too
    x0,y0,x1,y1 = box
    fill = _rgb(color)
    code = ldraw.split(".")[0]
    try:
        n = int(''.join([c for c in code if c.isdigit()]) or 0)
    except:
        n = 0

    if 4500 <= n < 4600:  # slopes
        d.polygon([(x0,y1), (x1,y1), (x1,y0)], fill=fill, outline=(40,40,40))
    elif code in ("3068",) or (3068 <= n < 3070):  # tile 2x2-ish
        d.rectangle((x0,y0,x1,y1), fill=tuple(int(c*0.85) for c in fill), outline=(50,50,50))
    else:  # bricks/plates generic
        d.rectangle((x0,y0,x1,y1), fill=fill, outline=(40,40,40))

def _count_by_part_color(parts: List[Dict]):
    c = Counter((p["ldraw"], p["color"]) for p in parts)
    return sorted(((ld, col, n) for (ld, col), n in c.items()), key=lambda t:(t[0], t[1]))

def _canvas(W: int, L: int, scale: int = SCALE, pli_w: int = PLI_W) -> Tuple[Image.Image, ImageDraw.ImageDraw, int, int, int, int]:
    img = Image.new("RGB", (MARGIN + L*scale + pli_w + MARGIN, MARGIN + W*scale + MARGIN), (245,245,245))
    d = ImageDraw.Draw(img)
    gx = MARGIN; gy = MARGIN
    # grid
    for x in range(L+1):
        d.line([(gx + x*scale, gy), (gx + x*scale, gy + W*scale)], fill=(220,220,220), width=1)
    for y in range(W+1):
        d.line([(gx, gy + y*scale), (gx + L*scale, gy + y*scale)], fill=(220,220,220), width=1)
    # PLI panel
    xoff = gx + L*scale
    d.rectangle([(xoff, gy), (xoff + pli_w, gy + W*scale)], outline=(205,205,205), fill=(252,252,252))
    d.text((xoff + 12, gy + 8), "Parts this step", fill=(20,20,20))
    return img, d, scale, gx, gy, xoff

def _draw_rect_label(d: ImageDraw.ImageDraw, x0,y0,x1,y1, fill, text):
    d.rectangle((x0,y0,x1,y1), fill=fill, outline=(30,30,30))
    d.text((x0+4, y0+4), text, fill=(0,0,0))

def _short(n: str) -> str:
    return n.split(" ", 1)[1] if " " in n else n

def draw_step_image(
    placements: List[Dict], step_id: int, W: int, L: int, out_path: str,
    scale: int = SCALE, pli_w: int = PLI_W
):
    img, d, s, gx, gy, xoff = _canvas(W, L, scale, pli_w)

    # previous steps (dim)
    for p in placements:
        if int(p.get("step", 0)) >= step_id:
            continue
        x0 = gx + p["x"]*s; y0 = gy + p["y"]*s
        x1 = gx + (p["x"]+p["l"])*s; y1 = gy + (p["y"]+p["w"])*s
        fill = tuple(int(c*0.35) for c in _rgb(p["color"]))
        _draw_rect_label(d, x0,y0,x1,y1, fill, _short(p["name"]))

    # current step (full color)
    new_parts = [p for p in placements if int(p.get("step", 0)) == step_id]
    for p in new_parts:
        x0 = gx + p["x"]*s; y0 = gy + p["y"]*s
        x1 = gx + (p["x"]+p["l"])*s; y1 = gy + (p["y"]+p["w"])*s
        _draw_rect_label(d, x0,y0,x1,y1, _rgb(p["color"]), _short(p["name"]))

    # PLI on the right with thumbnails
    rows = _count_by_part_color(new_parts)
    base_y = gy + 36
    for i, (ldraw, color, qty) in enumerate(rows):
        box = _part_thumb_box(i, xoff, base_y)
        _draw_part_thumb(d, box, ldraw, color)
        d.text((box[2] + 10, box[1] + 8), f"{ldraw}  {color}", fill=(40,40,40))
        d.text((box[2] + 10, box[1] + 26), f"×{qty}", fill=(40,40,40))

    img.save(out_path)

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

    # determine step_count
    if step_count is None:
        if any("step" in p for p in placements):
            step_count = 1 + max(int(p["step"]) for p in placements)
        else:
            step_count = H
            for p in placements:
                p["step"] = int(p.get("z", 0))

    # cap pages to avoid runaway renders
    page_limit = min(step_count, MAX_PAGES)

    placements = sorted(placements, key=lambda p: (int(p.get("step", 0)), p["y"], p["x"], p["ldraw"]))

    # render images
    for s in range(page_limit):
        out_path = os.path.join(steps_dir, f"step_{s:02d}.png")
        draw_step_image(placements, s, W, L, out_path)

    # HTML (shows whatever we rendered; warns if capped)
    css = """
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;color:#222}
    .btn{display:inline-block;margin-top:12px;padding:10px 14px;border-radius:10px;border:1px solid #ddd;text-decoration:none;color:#111}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px;margin-top:24px}
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
        html.append(f"<div class='muted'>Showing first {page_limit} of {step_count} steps (capped by MAX_PAGES={MAX_PAGES}).</div>")
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
