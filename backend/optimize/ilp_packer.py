# backend/optimize/ilp_packer.py
from typing import List, Dict, Tuple
import numpy as np
from ortools.sat.python import cp_model

# same parts as greedy packer
PARTS = [
    {"name":"Plate 2x4", "w":2, "l":4, "ldraw":"3020.dat"},
    {"name":"Plate 2x2", "w":2, "l":2, "ldraw":"3022.dat"},
    {"name":"Plate 1x2", "w":1, "l":2, "ldraw":"3023.dat"},
    {"name":"Plate 1x1", "w":1, "l":1, "ldraw":"3024.dat"},
]

PALETTE = ["red","black","light_gray","white"]

def _candidates_for_layer(layer: np.ndarray, below: np.ndarray | None) -> Tuple[List[Dict], Dict[Tuple[int,int], List[int]]]:
    H, W, L = 1, layer.shape[0], layer.shape[1]  # layer is [y,x]
    cands: List[Dict] = []
    cover: Dict[Tuple[int,int], List[int]] = {}
    z = 0  # single layer function

    def supported(y0, x0, w, l) -> bool:
        if below is None:
            return True
        # require at least 50% overlap with covered below
        return below[y0:y0+w, x0:x0+l].sum() >= (w*l)//2

    idx = 0
    for part in PARTS:
        w,l = part["w"], part["l"]
        for y in range(W - w + 1):
            for x in range(L - l + 1):
                region = layer[y:y+w, x:x+l]
                if region.sum() == w*l and supported(y,x,w,l):
                    cands.append({
                        "z": None, "y": y, "x": x, "w": w, "l": l,
                        "name": part["name"], "ldraw": part["ldraw"],
                    })
                    for yy in range(y, y+w):
                        for xx in range(x, x+l):
                            cover.setdefault((yy,xx), []).append(idx)
                    idx += 1
    return cands, cover

def pack_ilp(vox: np.ndarray, seed: int = 42) -> List[Dict]:
    # vox: [z,y,x] with 1 for occupied
    Z, W, L = vox.shape
    placements: List[Dict] = []
    covered_below = None

    for z in range(Z):
        layer = vox[z]
        if covered_below is None:
            below_mask = None
        else:
            below_mask = covered_below

        cands, cover = _candidates_for_layer(layer, below_mask)
        model = cp_model.CpModel()
        xs = [model.NewBoolVar(f"x_{i}") for i in range(len(cands))]

        # cover each occupied stud
        for (y,x), idxs in cover.items():
            if layer[y,x] == 1:
                model.Add(sum(xs[i] for i in idxs) >= 1)

        # minimize part count (can add weights for bigger plates to be preferred)
        model.Minimize(sum(xs))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        solver.parameters.num_search_workers = 8
        res = solver.Solve(model)

        # Start with all zeros; fill chosen placements
        covered = np.zeros_like(layer, dtype=np.uint8)
        if res in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for i, c in enumerate(cands):
                if solver.Value(xs[i]) == 1:
                    c2 = c.copy()
                    c2["z"] = z
                    c2["color"] = PALETTE[(z + c["y"] + c["x"]) % len(PALETTE)]
                    placements.append(c2)
                    covered[c["y"]:c["y"]+c["w"], c["x"]:c["x"]+c["l"]] = 1

        # fill any remaining studs with 1x1
        for y in range(W):
            for x in range(L):
                if layer[y,x] == 1 and covered[y,x] == 0:
                    placements.append({
                        "z": z, "y": y, "x": x, "w": 1, "l": 1,
                        "name": "Plate 1x1", "ldraw": "3024.dat",
                        "color": PALETTE[(z + y + x) % len(PALETTE)]
                    })
                    covered[y,x] = 1

        covered_below = covered  # next layer support

    return placements
