from typing import List, Dict
from collections import defaultdict
import csv, json, os

def make_bom(placements: List[Dict]):
    agg = defaultdict(int)
    for p in placements:
        key = (p["ldraw"], p["name"], p["color"])
        agg[key] += 1
    items = []
    for (ldraw, name, color), qty in sorted(agg.items(), key=lambda x:(x[0][0], x[0][2])):
        items.append({
            "part_id": ldraw.replace(".dat",""),
            "name": name,
            "color": color,
            "quantity": qty
        })
    return items

def write_bom(items, outdir):
    os.makedirs(outdir, exist_ok=True)
    # CSV
    csv_path = os.path.join(outdir, "bom.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["part_id","name","color","quantity"])
        w.writeheader()
        for it in items:
            w.writerow(it)
    # JSON
    json_path = os.path.join(outdir, "bom.json")
    with open(json_path, "w") as f:
        json.dump(items, f, indent=2)
    return csv_path, json_path
