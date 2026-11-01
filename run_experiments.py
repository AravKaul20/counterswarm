"""E1: scaling with threat count x condition. E2: node-loss resilience.
Writes results/results.json. Run after run_sanity.py passes."""
import json
import time
from pathlib import Path
import numpy as np
from sim import Simulation

OUT = Path(__file__).resolve().parent / "results" / "results.json"

CONDITIONS = ("full", "norelay", "homog")
THREAT_COUNTS = (4, 8, 12, 16)
SEEDS = range(10)

results = {"E1": [], "E2": []}


def summarize_events(m):
    """Replace the event list by its length; keep the first intercept time."""
    kills = [e[1] for e in m["events"] if e[0] == "intercept"]
    m["t_first_kill"] = min(kills) if kills else None
    m["events"] = len(m["events"])


t0 = time.time()

for cond in CONDITIONS:
    for n in THREAT_COUNTS:
        for seed in SEEDS:
            m = Simulation(dict(team=cond, n_threats=n, seed=100 * n + seed)).run()
            summarize_events(m)
            results["E1"].append(m)
            print(f"E1 {cond:8s} n={n:2d} seed={seed} rate={m['interception_rate']:.2f} "
                  f"tti={m['tti_mean'] and round(m['tti_mean'], 1)} uptime={m['uptime']:.2f} "
                  f"l2={m['l2_mean']:.2f} [{time.time() - t0:.0f}s]", flush=True)

# E2: kill 3 random defenders at t=15 s, 8 threats
T_KILL = 15.0
for cond in CONDITIONS:
    for seed in SEEDS:
        s = Simulation(dict(team=cond, n_threats=8, seed=500 + seed,
                            kills=[(T_KILL, 3)]))
        m = s.run()
        summarize_events(m)
        # connectivity series split before/after the kill
        ts = np.array(s.series["t"])
        con = np.array(s.series["connected"])
        lcf = np.array(s.series["lcf"])
        m["uptime_pre"] = float(con[ts < T_KILL].mean())
        m["uptime_post"] = float(con[ts >= T_KILL].mean()) if (ts >= T_KILL).any() else None
        m["lcf_pre"] = float(lcf[ts < T_KILL].mean())
        m["lcf_post"] = float(lcf[ts >= T_KILL].mean()) if (ts >= T_KILL).any() else None
        m["series"] = {"t": s.series["t"], "lcf": s.series["lcf"],
                       "l2": s.series["l2"]}
        results["E2"].append(m)
        print(f"E2 {cond:8s} seed={seed} rate={m['interception_rate']:.2f} "
              f"uptime pre={m['uptime_pre']:.2f} post={m['uptime_post']} "
              f"[{time.time() - t0:.0f}s]", flush=True)

with open(OUT, "w") as f:
    json.dump(results, f)
print(f"done in {time.time() - t0:.0f}s -> {OUT}")
