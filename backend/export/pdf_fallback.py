# backend/export/pdf_fallback.py
import os
from typing import Optional
from PIL import Image

def make_pdf_from_pngs(outdir: str, pdf_name: str = "instructions.pdf") -> Optional[str]:
    steps_dir = os.path.join(outdir, "instructions", "steps")
    candidates = []
    if os.path.isdir(steps_dir):
        candidates = sorted(
            os.path.join(steps_dir, f)
            for f in os.listdir(steps_dir)
            if f.lower().endswith(".png") and f.startswith("step_")
        )
    if not candidates:
        # fallback to any older pattern if present
        legacy = os.path.join(outdir, "instructions")
        if os.path.isdir(legacy):
            candidates = sorted(
                os.path.join(legacy, f)
                for f in os.listdir(legacy)
                if f.lower().endswith(".png")
            )
    if not candidates:
        return None

    images = [Image.open(p).convert("RGB") for p in candidates]
    pdf_path = os.path.join(outdir, pdf_name)
    images[0].save(pdf_path, save_all=True, append_images=images[1:])
    return pdf_path if os.path.isfile(pdf_path) else None
