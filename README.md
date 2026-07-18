# Counter-Swarm: Heterogeneous 3D Counter-Drone Swarm Defense

A fully 3D simulation of a heterogeneous defending swarm (sentinels /
interceptors / relays) protecting an asset against an evasive attacking swarm,
with volumetric sensing, 3D line-of-sight occlusion, lossy range-limited
communications, consensus-auction task allocation per connected component,
true 3D proportional-navigation guidance, and algebraic-connectivity-gradient
relay repositioning.

Research focus: **heterogeneous role allocation under partial 3D observability
and dynamic connectivity** — see `docs/design.md` and `paper/paper.tex`.

## Run

```
pip install numpy matplotlib
python run_sanity.py        # verification gate (run first)
python run_experiments.py   # E1 scaling + E2 node-loss  -> results/results.json  (~10 min)
python make_plots.py        # figures + summary table    -> results/*.png
python export_run.py        # record demo run            -> viewer/data.js
```

## 3D viewer

After `export_run.py`, open `viewer/index.html` in a browser (or
`python -m http.server --directory viewer` and browse to it). Orbit with the
mouse; play/pause, speed, and a time scrubber at the bottom. Amber = sentinel,
cyan = interceptor, green = relay, red = threat; grey lines are live comm
links; flashes mark intercepts.

## Layout

- `sim/config.py` — role capability profiles and constants
- `sim/world.py` — building field, segment-AABB line-of-sight, obstacle repulsion
- `sim/comms.py` — comm graph, Laplacian λ₂/Fiedler vector, components
- `sim/guidance.py` — 3D PN, waypoint PD, relay λ₂-gradient, separation
- `sim/allocation.py` — consensus greedy auctions (interceptor-threat, sentinel-station)
- `sim/engine.py` — entities, per-tick loop, metrics, frame recording
- `paper/paper.tex` — paper draft (compile on Overleaf; needs `results/*.png`)
- `OUTREACH.md` — plain-language summary for outreach email
