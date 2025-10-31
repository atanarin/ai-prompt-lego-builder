# Prompt LEGO MVP (Checkpoint Build)

This is a **checkpoint MVP** for a Prompt → LEGO pipeline you can run locally.
It focuses on the **prompt path** (no image reconstruction yet), generates a simple **voxelized shape**
from a text prompt, packs it with a small library of **plates** (2x4, 2x2, 1x2, 1x1), exports an **LDraw** file,
creates a **BOM** (CSV/JSON), and renders **layer-by-layer instruction PNGs** + an **HTML manual**.

> Uses your OpenAI key only for prompt parsing via function calling (optional). If you don't set it,
> a local rules-based parser is used.

## Features (this checkpoint)
- FastAPI backend with `/from_prompt` endpoint
- Prompt parser → JSON design spec
- Parametric voxelizer (spaceship_v1)
- Greedy layer-by-layer plate packing (2x4 → 2x2 → 1x2 → 1x1)
- Stability heuristic: every part must be on base layer or overlap occupied voxels below
- LDraw exporter (`.ldr`) with standard plate part IDs
- BOM generator (`bom.csv`, `bom.json`)
- Instruction images (per-layer PNG) + `instructions.html`
- Deterministic seed for reproducibility

## Getting Started

### 1) Python env
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Env
Create `.env` in project root (optional if you want OpenAI parsing):
```
OPENAI_API_KEY=sk-...
```

### 3) Run server
```bash
uvicorn backend.api:app --reload
```

### 4) Try it
```bash
curl -X POST http://127.0.0.1:8000/from_prompt   -H "Content-Type: application/json"   -d '{"prompt":"sleek red micro spaceship, ~16 studs long, <150 parts"}'
```

Outputs are under `outputs/session_<timestamp>/`:
- `model.ldr`
- `bom.csv`, `bom.json`
- `instructions/step_*.png`
- `instructions.html`

Open `instructions.html` in a browser to see a simple step-by-step guide.

## Notes
- This is a **checkpoint** build prioritizing end-to-end flow and determinism.
- Parts are **plates only**: 2x4 (3020.dat), 2x2 (3022.dat), 1x2 (3023.dat), 1x1 (3024.dat).
- Coordinates are placed on a simple stud grid; rotations are currently axis-aligned only.
- Instruction rendering is a 2D layer view (top-down). LPub3D integration can be added later.

## Next Steps
- Add image path (SAM2 + depth → mesh → voxelizer)
- Replace greedy packer with CP-SAT ILP (OR-Tools) for better coverage & fewer parts
- Add color availability constraints via Rebrickable API
- Add submodel grouping for nicer instructions
- Export BrickLink wanted list
