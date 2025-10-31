# backend/export/ldraw_writer.py
from typing import List, Dict
from collections import defaultdict
import os

LDRAW_COLOR = {"red": 4, "black": 0, "light_gray": 7, "white": 15, "blue": 1, "green": 2, "yellow": 14}
STUD = 20
PLATE = 8

def _part_line(p: Dict) -> str:
    z = int(p.get("z", 0))
    X = int((p["x"] + p["l"] / 2.0) * STUD)
    Y = int(z * PLATE)
    Z = int((p["y"] + p["w"] / 2.0) * STUD)
    col = LDRAW_COLOR.get(p["color"], 7)
    return f"1 {col} {X} {Y} {Z}  1 0 0  0 1 0  0 0 1 {p['ldraw']}"

def write_assembly(placements: List[Dict], outdir: str, H: int) -> str:
    """
    Writes:
      step_00.ldr, step_01.ldr, ...
      model.ldr (top-level) referencing each step with 0 STEP between.
    Falls back to per-layer if 'step' not in placements.
    """
    os.makedirs(outdir, exist_ok=True)
    if any("step" in p for p in placements):
        key = "step"
        steps = sorted(set(int(p["step"]) for p in placements))
        label = "step"
    else:
        key = "z"
        steps = list(range(H))
        label = "layer"

    buckets = defaultdict(list)
    for p in placements:
        buckets[int(p.get(key, 0))].append(p)

    # write subfiles
    subfiles = []
    for s in steps:
        path = os.path.join(outdir, f"{label}_{s:02d}.ldr")
        with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write(f"0 FILE {label}_{s:02d}.ldr\n")
            fh.write(f"0 // Generated submodel for {label} {s}\n")
            for p in sorted(buckets[s], key=lambda q: (q["y"], q["x"], q["ldraw"])):
                fh.write(_part_line(p) + "\n")
        subfiles.append(path)

    # top-level
    model_path = os.path.join(outdir, "model.ldr")
    with open(model_path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write("0 FILE model.ldr\n")
        fh.write(f"0 // Main assembly: each {label} as a STEP\n")
        first = True
        for s, sf in zip(steps, subfiles):
            if not first:
                fh.write("0 STEP\n")
            first = False
            fh.write(f"1 16 0 0 0  1 0 0  0 1 0  0 0 1 {os.path.basename(sf)}\n")
    return model_path
