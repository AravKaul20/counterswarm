"""Record one full-team demo run and export it for the Three.js viewer."""
import json
from pathlib import Path
import numpy as np
from sim import Simulation
from sim import config as C

OUT = Path(__file__).resolve().parent / "viewer" / "data.js"

s = Simulation(dict(team="full", n_threats=10, seed=42, record=True))
m = s.run()
print(f"demo run: killed={m['killed']} leaked={m['leaked']} t_end={m['t_end']:.0f}s "
      f"uptime={m['uptime']:.2f} l2={m['l2_mean']:.2f} frames={len(s.frames)}")

data = {
    "roles": [a.role for a in s.defenders],
    "boxes": [[list(np.round(lo, 1)), list(np.round(hi, 1))] for lo, hi in s.boxes],
    "asset": list(np.round(C.ASSET_POS, 1)),
    "events": [list(e) for e in m["events"]],
    "frames": s.frames,
}
with open(OUT, "w") as f:
    f.write("window.RUN = ")
    json.dump(data, f)
    f.write(";")
print("wrote viewer/data.js")
