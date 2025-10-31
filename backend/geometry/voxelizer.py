import numpy as np
from ..utils.spec_schema import DesignSpec

def spaceship_voxels(spec: DesignSpec) -> np.ndarray:
    L, W, H = spec.length_studs, spec.width_studs, spec.height_layers
    vox = np.zeros((H, W, L), dtype=np.uint8)  # [z,y,x] layers, rows, cols

    # fuselage: a central block tapered at nose and tail
    for z in range(H):
        for y in range(W):
            for x in range(L):
                # taper along length (x)
                center_y = W/2.0
                dy = abs(y - center_y + 0.5)
                max_width = max(2, W * (0.9 - 0.6*abs((x - L/2)/(L/2+1e-6))))
                if dy*2 < max_width:
                    # height falloff toward edges
                    edge_factor = 1.0 - (dy / (W/2+1e-6))
                    max_h_at_y = max(2, int(H * (0.6 + 0.3*edge_factor)))
                    if z < max_h_at_y:
                        vox[z,y,x] = 1

    # carve wings: thin layer extending sideways near mid-height
    wing_z = max(1, H//3)
    for x in range(L):
        span = max(2, int(W*0.3 + (x/(L-1+1e-6))*W*0.2))
        y_mid = W//2
        for y in range(max(0, y_mid-span), min(W, y_mid+span)):
            if wing_z < H:
                vox[wing_z, y, x] = 1

    # cockpit notch on top-front
    for z in range(H-1, max(H-3, 0), -1):
        for y in range(W//3, 2*W//3):
            for x in range(L//4, L//2):
                vox[z,y,x] = 0

    return vox

def make_voxels(spec: DesignSpec) -> np.ndarray:
    if spec.category == "spaceship":
        return spaceship_voxels(spec)
    # Fallback simple box
    vox = np.zeros((spec.height_layers, spec.width_studs, spec.length_studs), dtype=np.uint8)
    vox[:,:,:] = 1
    return vox
