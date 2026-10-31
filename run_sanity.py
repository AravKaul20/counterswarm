"""Self-verification gate: run before trusting any full-scale result.

Checks (all printed with pass/fail):
  1. 1v1, no evasion  -> interceptor converges and kills.
  2. 1v1, evasive     -> still killed (may take longer).
  3. Relay sweep      -> mesh uptime / lambda2 improve with relay count.
  4. Occlusion sanity -> low-flying threats are tracked less than high ones.
Physical bounds (speed/accel <= role limits) are asserted via debug=True.
"""
import sys
import numpy as np
from sim import Simulation


def check(name, cond, detail):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")
    return cond


ok = True

# 1) single interceptor vs single non-evasive threat
m = Simulation(dict(team={"sentinel": 2, "interceptor": 1, "relay": 1},
                    n_threats=1, evasion=False, seed=1, debug=True)).run()
ok &= check("1v1 straight-runner intercepted", m["killed"] == 1,
            f"killed={m['killed']} tti={m['tti_mean']}")

# 2) evasive
ttis = []
kills = 0
for s in range(3):
    m = Simulation(dict(team={"sentinel": 2, "interceptor": 1, "relay": 1},
                        n_threats=1, evasion=True, seed=10 + s, debug=True)).run()
    kills += m["killed"]
    if m["tti_mean"]:
        ttis.append(m["tti_mean"])
ok &= check("1v1 evasive intercepted (3 seeds)", kills == 3,
            f"kills={kills}/3 tti={np.round(ttis, 1)}")

# 3) relay count sweep: uptime and lambda2 should rise with relays
rows = []
for nr in (0, 2, 4):
    ups, l2s = [], []
    for s in range(3):
        team = {"sentinel": 4, "interceptor": 8}
        if nr:
            team["relay"] = nr
        m = Simulation(dict(team=team, n_threats=8, seed=20 + s)).run()
        ups.append(m["uptime"])
        l2s.append(m["l2_mean"])
    rows.append((nr, np.mean(ups), np.mean(l2s)))
    print(f"    relays={nr}: uptime={np.mean(ups):.3f} l2={np.mean(l2s):.3f}")
ok &= check("relays improve mesh", rows[0][1] <= rows[2][1] and rows[0][2] <= rows[2][2],
            f"uptime {rows[0][1]:.3f}->{rows[2][1]:.3f}, l2 {rows[0][2]:.3f}->{rows[2][2]:.3f}")

# 4) occlusion: identical low-altitude runs with buildings vs without
import sim.config as C
C.THREAT["cruise_alt"] = (12.0, 20.0)
tracked = {}
for label, keep_boxes in (("buildings", True), ("open", False)):
    vals = []
    for s in range(3):
        s_ = Simulation(dict(team={"sentinel": 4, "relay": 2}, n_threats=8, seed=30 + s))
        if not keep_boxes:
            s_.boxes = []
        vals.append(s_.run()["tracked_mean"])
    tracked[label] = np.mean(vals)
    print(f"    {label}: tracked={tracked[label]:.3f}")
ok &= check("3D occlusion reduces tracking of low-flying threats",
            tracked["buildings"] < tracked["open"],
            f"buildings={tracked['buildings']:.3f} open={tracked['open']:.3f}")

print("\nALL SANITY CHECKS PASSED" if ok else "\nSANITY FAILURES -- do not run experiments")
sys.exit(0 if ok else 1)
