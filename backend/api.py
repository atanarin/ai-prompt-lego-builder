# backend/api.py
import os
import time
import uuid
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from .planners.prompt_parser import parse_prompt
from .geometry.voxelizer import make_voxels
from .optimize.greedy_packer import pack_greedy
from .export.ldraw_writer import write_assembly
from .export.bom import make_bom, write_bom
from .export.instructions import write_instruction_set
from .export.pdf_fallback import make_pdf_from_pngs
from .planners.step_planner import plan_steps_connectivity_batched

app = FastAPI(title="Prompt LEGO MVP (Headless, Batched Steps)")

class PromptIn(BaseModel):
    prompt: str
    seed: Optional[int] = 42
    solver: Optional[str] = "greedy"
    batch_size: Optional[int] = 8

@app.post("/from_prompt")
def from_prompt(inp: PromptIn):
    # --- parse & session
    spec = parse_prompt(inp.prompt)
    if inp.seed is not None:
        spec.seed = inp.seed

    ts = time.strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{ts}_{uuid.uuid4().hex[:6]}"
    outdir = os.path.join("outputs", session_id)
    os.makedirs(outdir, exist_ok=True)

    # --- voxelize
    t0 = time.time()
    vox = make_voxels(spec)  # ndarray [H,W,L]
    H, W, L = vox.shape
    print(f"[TIMER] voxelize: {time.time()-t0:.2f}s  grid=({H},{W},{L})")

    # --- pack parts
    t1 = time.time()
    placements = pack_greedy(vox, seed=spec.seed)
    print(f"[TIMER] pack_greedy: {time.time()-t1:.2f}s  placements={len(placements)}")

    # --- plan steps (connectivity + small batches)
    batch = int(inp.batch_size) if inp.batch_size and inp.batch_size > 0 else 8
    t2 = time.time()
    placements, step_count = plan_steps_connectivity_batched(placements, batch_size=batch)
    print(f"[TIMER] plan_steps: {time.time()-t2:.2f}s  steps={step_count}  batch={batch}")

    # --- write LDraw assembly (optional, for LPub3D later)
    t3 = time.time()
    model_path = write_assembly(placements, outdir, H)
    print(f"[TIMER] write_assembly: {time.time()-t3:.2f}s")

    # --- BOM
    t4 = time.time()
    items = make_bom(placements)
    csv_path, json_path = write_bom(items, outdir)
    print(f"[TIMER] bom: {time.time()-t4:.2f}s  items={len(items)}")

    # --- Render pages (PNG with PLI) — first pass with no PDF link
    t5 = time.time()
    write_instruction_set(
        placements=placements,
        outdir=outdir,
        H=H, W=W, L=L,
        spec=spec.model_dump(),
        pdf_path=None,
        step_count=step_count
    )
    print(f"[TIMER] render PNGs: {time.time()-t5:.2f}s")

    # --- Stitch PDF
    t6 = time.time()
    pdf_path = make_pdf_from_pngs(outdir)
    print(f"[TIMER] stitch PDF: {time.time()-t6:.2f}s")

    # --- Update HTML with a working PDF link
    write_instruction_set(
        placements=placements,
        outdir=outdir,
        H=H, W=W, L=L,
        spec=spec.model_dump(),
        pdf_path=pdf_path,
        step_count=step_count
    )

    return {
        "session": session_id,
        "spec": spec.model_dump(),
        "counts": {
            "placements": len(placements),
            "studs": int(vox.sum()),
            "steps": step_count,
        },
        "outputs": {
            "ldr": model_path,
            "bom_csv": csv_path,
            "bom_json": json_path,
            "instructions_html": os.path.join(outdir, "instructions.html"),
            "instructions_pdf": pdf_path if (pdf_path and os.path.isfile(pdf_path)) else None,
        },
    }
