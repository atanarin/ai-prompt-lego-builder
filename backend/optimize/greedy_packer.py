from typing import List, Tuple, Dict
import numpy as np
import random

# Define plate parts with sizes (studs) and LDraw part IDs
PARTS = [
    {"name":"Plate 2x4", "w":2, "l":4, "ldraw":"3020.dat"},
    {"name":"Plate 2x2", "w":2, "l":2, "ldraw":"3022.dat"},
    {"name":"Plate 1x2", "w":1, "l":2, "ldraw":"3023.dat"},
    {"name":"Plate 1x1", "w":1, "l":1, "ldraw":"3024.dat"},
]

def pack_greedy(vox: np.ndarray, seed: int = 42) -> List[Dict]:
    """Greedy layer-by-layer packing with plates. 
    vox shape: [z,y,x] occupied==1
    Returns list of parts dict: {z,y,x,w,l,name,ldraw,color}
    """
    rng = random.Random(seed)
    H, W, L = vox.shape
    # Start with all zeros for coverage tracking
    covered = np.zeros_like(vox, dtype=np.uint8)
    placements = []

    # simple palette rotation
    palette_cycle = ["red","black","light_gray","white","blue","green","yellow"]

    for z in range(H):
        # ensure support: restrict to positions where below is base or already covered
        support = (z == 0) or (covered[z-1] == 1)

        # Try to place largest plates first
        for part in PARTS:
            w, l = part["w"], part["l"]
            for y in range(W - w + 1):
                for x in range(L - l + 1):
                    # check if area needs coverage and is supported
                    region = vox[z, y:y+w, x:x+l]
                    if region.sum() == w*l and (z==0 or covered[z-1, y:y+w, x:x+l].sum() >= int(0.5*w*l)):
                        # ensure not already covered
                        if covered[z, y:y+w, x:x+l].sum() == 0:
                            # place it
                            placements.append({
                                "z": z, "y": y, "x": x, "w": w, "l": l,
                                "name": part["name"], "ldraw": part["ldraw"],
                                "color": palette_cycle[(z + y + x) % len(palette_cycle)]
                            })
                            covered[z, y:y+w, x:x+l] = 1

        # Fill any uncovered but occupied voxels with 1x1
        for y in range(W):
            for x in range(L):
                if vox[z,y,x] == 1 and covered[z,y,x] == 0:
                    # check support
                    if z==0 or covered[z-1,y,x]==1:
                        placements.append({
                            "z": z, "y": y, "x": x, "w": 1, "l": 1,
                            "name": "Plate 1x1", "ldraw": "3024.dat",
                            "color": palette_cycle[(z + y + x) % len(palette_cycle)]
                        })
                        covered[z,y,x] = 1

    return placements
