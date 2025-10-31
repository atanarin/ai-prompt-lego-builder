# backend/planners/step_planner.py
from typing import List, Dict, Tuple, Set
from collections import defaultdict
import math

Cell = Tuple[int, int, int]  # (z, x, y)

def _cells(p: Dict) -> Set[Cell]:
    z = int(p.get("z", 0))
    x0, y0 = int(p["x"]), int(p["y"])
    w, l = int(p["w"]), int(p["l"])
    return {(z, x0 + dx, y0 + dy) for dx in range(l) for dy in range(w)}

def _center_xy(p: Dict) -> Tuple[float, float]:
    return (float(p["x"]) + float(p["l"])/2.0, float(p["y"]) + float(p["w"])/2.0)

def _touches_same_z(placed: Set[Cell], cells: Set[Cell]) -> bool:
    for (z, x, y) in cells:
        for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if (z, nx, ny) in placed:
                return True
    return False

def _supported(below_occ: Set[Tuple[int,int]], cells: Set[Cell]) -> bool:
    for (z, x, y) in cells:
        if z == 0:
            continue
        if (x, y) not in below_occ:
            return False
    return True

def _build_below_occ(placements: List[Dict]) -> dict:
    occ_by_z = defaultdict(set)
    for p in placements:
        for (_, x, y) in _cells(p):
            occ_by_z[int(p.get("z", 0))].add((x, y))
    return occ_by_z

def _nearest_to_cluster(p: Dict, cluster_centers):
    if not cluster_centers:
        return 0.0
    px, py = _center_xy(p)
    return min(math.hypot(px-cx, py-cy) for (cx, cy) in cluster_centers)

def plan_steps_connectivity_batched(
    placements: List[Dict],
    batch_size: int = 8,
    log_every: int = 25
) -> Tuple[List[Dict], int]:
    """
    Connectivity + support, small batches, with hard safety rails.
    Always assigns a step to at least one piece per iteration until everything is placed.
    """
    if not placements:
        return placements, 0

    MAX_ITERS = 10 * len(placements)  # hard guard
    occ_by_z = _build_below_occ(placements)

    by_z = defaultdict(list)
    for p in placements:
        by_z[int(p.get("z", 0))].append(p)
    for z in by_z:
        by_z[z].sort(key=lambda q: (int(q["y"]), int(q["x"]), q["ldraw"]))

    placed_cells: Set[Cell] = set()
    cluster_centers_by_z = defaultdict(list)

    remaining: List[Dict] = []
    for z in sorted(by_z.keys()):
        remaining.extend(by_z[z])

    step = 0
    assigned = 0
    N = len(placements)
    iters = 0

    while assigned < N:
        iters += 1
        if iters > MAX_ITERS:
            # fail-safe: dump everything left into one final step
            for p in remaining:
                p["step"] = step
            assigned += len(remaining)
            remaining.clear()
            print(f"[WARN] step planner hit MAX_ITERS; forced completion at step {step}.")
            step += 1
            break

        strict: List[Dict] = []
        bridges: List[Tuple[float, Dict]] = []

        for p in remaining:
            cells = _cells(p)
            z = int(p.get("z", 0))
            if not _supported(occ_by_z[z-1] if z > 0 else set(), cells):
                continue
            has_any_on_z = any(c[0] == z for c in placed_cells)
            if has_any_on_z:
                if _touches_same_z(placed_cells, cells):
                    strict.append(p)
                else:
                    bridges.append((_nearest_to_cluster(p, cluster_centers_by_z[z]), p))
            else:
                strict.append(p)  # seed piece for this z

        picked: List[Dict] = strict[:batch_size]

        if not picked:
            # Allow exactly one bridge (closest) to seed adjacency on this z
            if bridges:
                bridges.sort(key=lambda t: t[0])
                picked.append(bridges[0][1])
            else:
                # last resort: take any supported piece to ensure progress
                for p in remaining:
                    cells = _cells(p)
                    z = int(p.get("z", 0))
                    if _supported(occ_by_z[z-1] if z > 0 else set(), cells):
                        picked.append(p)
                        break
                if not picked:
                    # truly pathological — force pick the first remaining
                    picked.append(remaining[0])

        # assign step & update
        for p in picked:
            p["step"] = step
            z = int(p.get("z", 0))
            for c in _cells(p):
                placed_cells.add(c)
            cx, cy = _center_xy(p)
            cluster_centers_by_z[z].append((cx, cy))

        ids = set(id(p) for p in picked)
        remaining = [p for p in remaining if id(p) not in ids]

        assigned += len(picked)
        if step % log_every == 0:
            print(f"[INFO] step {step}: placed {assigned}/{N}")
        step += 1

    return placements, step
