import os, re
from typing import Dict, Any
from .rules import COLOR_ALIASES
from ..utils.spec_schema import DesignSpec

def parse_prompt(prompt: str) -> DesignSpec:
    # Very simple rule-based parsing; prefer numbers from prompt when present.
    prompt_low = prompt.lower()

    # length in studs
    length = 16
    m = re.search(r"(\d+)\s*stud", prompt_low)
    if m:
        length = max(4, min(64, int(m.group(1))))

    # complexity / part cap
    part_cap = 200
    if "<" in prompt_low and "part" in prompt_low:
        m2 = re.search(r"<\s*(\d+)\s*part", prompt_low)
        if m2:
            part_cap = max(50, min(5000, int(m2.group(1))))

    # category
    category = "spaceship"
    for c in ["spaceship","car","house","creature","robot","boat","plane"]:
        if c in prompt_low:
            category = c
            break

    # colors
    palette = []
    for color, aliases in COLOR_ALIASES.items():
        if any(a in prompt_low for a in aliases):
            palette.append(color)
    if not palette:
        palette = ["red","black","light_gray"]

    # width/height basic heuristics from length
    width = max(4, min(64, length//2))
    height = max(3, min(64, length//3))

    return DesignSpec(
        category=category,
        length_studs=length,
        width_studs=width,
        height_layers=height,
        palette=palette,
        part_cap=part_cap,
        style="sleek" if "sleek" in prompt_low else "blocky" if "blocky" in prompt_low else "default",
        symmetry="bilateral",
        stability_target="basic",
    )
