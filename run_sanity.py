"""Self-verification gate: run before trusting any full-scale result.
Exits non-zero if any check fails.

  1. 1v1, no evasion: a lone interceptor kills a straight-running threat.
  2. 1v1, evasive: it kills an evasive threat on each of 3 seeds.
  3. Kinematic limits: speeds and accelerations recomputed by finite
     differences from the recorded positions (not read back from the
     controller's clamped commands) stay within each aircraft's limits.
     Samples next to a hard altitude-floor contact are excluded from the
     acceleration test and counted: the floor zeroes a descent in one step,
     an impulse outside the point-mass limits (see paper, Limitations).
  4. Relays at fixed team size: swapping 4 of 12 interceptors for 4 relays
     (16 defenders either way) raises mean lambda2 on every one of 10 paired
     seeds and raises mesh uptime on average over them. lambda2 edge weights
     scale with each link's radio range, so part of its rise comes from the
     relays' longer radios; uptime is a plain connected/not-connected count.
  5. Occlusion: with low-flying threats, buildings lower mean track coverage
     relative to the same 10 seeds with the buildings removed (paired).

Checks 4 and 5 test the direction of a paired mean over fixed seeds chosen
before looking at the results; they are not significance tests. The effect
sizes are printed. Runtime is about 2 minutes on one core.
"""
import sys
import numpy as np
from sim import Simulation
import sim.config as C

SEEDS = range(3000, 3010)          # paired seeds for checks 4 and 5
DEF_FLOOR, THR_FLOOR = 2.0, 5.0    # hard altitude floors in sim/engine.py


def check(name, cond, detail):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")
    return bool(cond)


def run_traced(sim):
    """Run sim to completion. Returns (worst speed / vmax, worst accel / amax,
    excluded floor samples, metrics), all from finite differences of recorded
    positions of every aircraft alive at the start of each step."""
    dt = C.DT
    worst_v = worst_a = 0.0
    floor_samples = 0
    prev_v, prev_floor = {}, {}
    while sim.tick < int(C.SIM_TIME / dt) and any(th.alive for th in sim.threats):
        ents = [(("d", a.idx), a, a.vmax, a.amax, DEF_FLOOR) for a in sim.defenders if a.alive]
        ents += [(("t", th.tid), th, C.THREAT["vmax"], C.THREAT["amax"], THR_FLOOR)
                 for th in sim.threats if th.alive]
        before = {k: e.p.copy() for k, e, *_ in ents}
        sim.step()
        cur_v, cur_floor = {}, {}
        for k, e, vmax, amax, z_floor in ents:
            v = (e.p - before[k]) / dt
            at_floor = e.p[2] <= z_floor + 1e-9
            worst_v = max(worst_v, np.linalg.norm(v) / vmax)
            if k in prev_v:
                if at_floor or prev_floor[k]:
                    floor_samples += 1
                else:
                    worst_a = max(worst_a, np.linalg.norm(v - prev_v[k]) / dt / amax)
            cur_v[k], cur_floor[k] = v, at_floor
        prev_v, prev_floor = cur_v, cur_floor
    return worst_v, worst_a, floor_samples, sim.metrics()


def paired(a, b):
    d = np.asarray(b) - np.asarray(a)
    return d, d.mean(), d.std(ddof=1) / np.sqrt(len(d))


def main():
    ok = True
    worst = []  # (label, v ratio, a ratio, floor samples)
    one_v_one = {"sentinel": 2, "interceptor": 1, "relay": 1}

    # 1) single interceptor vs single non-evasive threat
    wv, wa, fl, m = run_traced(Simulation(dict(team=one_v_one, n_threats=1,
                                               evasion=False, seed=1)))
    worst.append(("1v1 straight", wv, wa, fl))
    ok &= check("1v1 straight-runner intercepted", m["killed"] == 1,
                f"killed={m['killed']} tti={m['tti_mean']}")

    # 2) evasive
    ttis, kills = [], 0
    for s in range(3):
        wv, wa, fl, m = run_traced(Simulation(dict(team=one_v_one, n_threats=1,
                                                   evasion=True, seed=10 + s)))
        worst.append((f"1v1 evasive seed {10 + s}", wv, wa, fl))
        kills += m["killed"]
        if m["tti_mean"]:
            ttis.append(m["tti_mean"])
    ok &= check("1v1 evasive intercepted (3 seeds)", kills == 3,
                f"kills={kills}/3 tti={np.round(ttis, 1)}")

    # 3) kinematic limits, also on one full-size run per team
    for team in ("full", "norelay", "homog"):
        wv, wa, fl, _ = run_traced(Simulation(dict(team=team, n_threats=8, seed=SEEDS[0])))
        worst.append((team, wv, wa, fl))
    v_ratio = max(w[1] for w in worst)
    a_ratio = max(w[2] for w in worst)
    n_floor = sum(w[3] for w in worst)
    ok &= check("speed limits hold (from recorded positions)", v_ratio <= 1.0 + 1e-6,
                f"max speed / vmax = {v_ratio:.6f}")
    ok &= check("acceleration limits hold away from the altitude floor",
                a_ratio <= 1.0 + 1e-6,
                f"max accel / amax = {a_ratio:.6f}; {n_floor} floor-contact samples excluded")

    # 4) relays vs interceptors at fixed team size (16 defenders)
    res = {}
    for nr in (0, 4):
        team = {"sentinel": 4, "interceptor": 12 - nr}
        if nr:
            team["relay"] = nr
        ms = [Simulation(dict(team=team, n_threats=8, seed=s)).run() for s in SEEDS]
        res[nr] = ms
        print(f"    relays={nr} interceptors={12 - nr}: "
              f"uptime={np.mean([m['uptime'] for m in ms]):.3f} "
              f"lcf={np.mean([m['lcf_mean'] for m in ms]):.3f} "
              f"l2={np.mean([m['l2_mean'] for m in ms]):.3f}")
    d_l2, _, _ = paired([m["l2_mean"] for m in res[0]], [m["l2_mean"] for m in res[4]])
    d_up, mu_up, se_up = paired([m["uptime"] for m in res[0]], [m["uptime"] for m in res[4]])
    ok &= check("4 relays raise lambda2 on every paired seed", np.all(d_l2 > 0),
                f"min d_l2={d_l2.min():.3f} over {len(d_l2)} seeds")
    ok &= check("4 relays raise mean mesh uptime (paired)", mu_up > 0,
                f"d_uptime={mu_up:+.3f} +- {se_up:.3f} (SE); "
                f"higher on {int(np.sum(d_up > 0))}/{len(d_up)} seeds")

    # 5) occlusion: identical low-altitude seeds with buildings vs without
    saved = C.THREAT["cruise_alt"]
    C.THREAT["cruise_alt"] = (12.0, 20.0)
    tracked = {}
    for label, keep_boxes in (("buildings", True), ("open", False)):
        vals = []
        for s in SEEDS:
            sim = Simulation(dict(team={"sentinel": 4, "relay": 2}, n_threats=8, seed=s))
            if not keep_boxes:
                sim.boxes = []
            vals.append(sim.run()["tracked_mean"])
        tracked[label] = vals
        print(f"    {label}: tracked={np.mean(vals):.3f}")
    C.THREAT["cruise_alt"] = saved
    d_tr, mu_tr, se_tr = paired(tracked["open"], tracked["buildings"])
    ok &= check("buildings reduce tracking of low-flying threats (paired)", mu_tr < 0,
                f"d_tracked={mu_tr:+.3f} +- {se_tr:.3f} (SE); "
                f"lower on {int(np.sum(d_tr < 0))}/{len(d_tr)} seeds")

    print("\nALL SANITY CHECKS PASSED" if ok else "\nSANITY FAILURES -- do not run experiments")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
