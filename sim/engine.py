"""Simulation engine: entities, per-tick loop, metrics, and frame recording."""
import numpy as np
from . import config as C
from .world import make_buildings, los_clear, clear_point, box_repulse
from .comms import build_graph, fiedler, components
from .guidance import unit, pn_accel, goto, relay_accel, avoidance
from .allocation import auction_interceptors, auction_sentinels, station_points

TEAMS = {
    "full": {"sentinel": 4, "interceptor": 8, "relay": 4},
    "norelay": {"sentinel": 4, "interceptor": 12},
    "homog": {"generalist": 16},
}


class Agent:
    def __init__(self, idx, role, p):
        prof = C.ROLES[role]
        self.idx = idx
        self.role = role
        self.p = np.array(p, dtype=float)
        self.v = np.zeros(3)
        self.vmax = prof["vmax"]
        self.amax = prof["amax"]
        self.cruise = prof["cruise"]
        self.comm = prof["comm"]
        self.sensor = prof["sensor"]
        self.s_range = prof.get("s_range", 0.0)
        self.s_half = prof.get("s_half", 0.0)
        self.fuel = prof.get("fuel", np.inf)
        self.alive = True
        self.tracks = {}          # tid -> (pos, vel, timestamp)
        self.assign = None        # threat id (interceptor/generalist)
        self.station = None       # station index (sentinel)
        self.home = self.p.copy() # idle/ready point
        self.can_intercept = role in ("interceptor", "generalist")


class Threat:
    def __init__(self, tid, p, rng):
        self.tid = tid
        self.p = np.array(p, dtype=float)
        self.v = np.zeros(3)
        self.alive = True
        self.outcome = None       # 'killed' | 'leaked'
        self.t_out = None
        self.omega = rng.uniform(0.4, 0.9)      # weave frequency [rad/s]
        self.phase = rng.uniform(0, 2 * np.pi)
        self.cruise_alt = rng.uniform(*C.THREAT["cruise_alt"])
        self.jink_dir = np.zeros(3)
        self.jink_until = -1.0


def ring(n, radius, alt, phase=0.0):
    az = np.linspace(0, 2 * np.pi, n, endpoint=False) + phase
    return [np.array([radius * np.cos(a), radius * np.sin(a), alt]) for a in az]


class Simulation:
    def __init__(self, scenario):
        self.sc = dict(team="full", n_threats=8, evasion=True, kills=(),
                       seed=0, world_seed=7, record=False, debug=False)
        self.sc.update(scenario)
        self.rng = np.random.default_rng(self.sc["seed"])
        self.boxes = make_buildings(np.random.default_rng(self.sc["world_seed"]))
        self.t = 0.0
        self.tick = 0
        self.stations = station_points(4)

        # defenders
        self.defenders = []
        team = TEAMS[self.sc["team"]] if isinstance(self.sc["team"], str) else self.sc["team"]
        for role, count in team.items():
            if role == "sentinel":
                pts = [self.stations[i % 4] + np.array([0, 0, 0.0]) for i in range(count)]
            elif role == "interceptor":
                pts = ring(count, 150, 80)
            elif role == "relay":
                pts = ring(count, 120, 85, phase=0.4)
            else:
                pts = ring(count, 200, 100)
            for p in pts:
                self.defenders.append(
                    Agent(len(self.defenders), role, clear_point(p, self.boxes)))

        # threats: two clustered approach azimuths
        n = self.sc["n_threats"]
        cl = self.rng.uniform(0, 2 * np.pi, size=2)
        self.threats = []
        for i in range(n):
            az = cl[i % 2] + self.rng.uniform(-0.3, 0.3)
            r = self.rng.uniform(750, 900)
            alt = self.rng.uniform(60, 120)
            self.threats.append(Threat(i, [r * np.cos(az), r * np.sin(az), alt], self.rng))

        self.kill_schedule = sorted(self.sc["kills"])  # [(t, n_agents)]
        self.events = []
        self.series = {"t": [], "l2": [], "lcf": [], "connected": [], "tracked": []}
        self.frames = [] if self.sc["record"] else None
        self._l2, self._fvec, self._comps = 0.0, None, [[]]

    # ------------------------------------------------------------------ loop
    def run(self):
        max_ticks = int(C.SIM_TIME / C.DT)
        while self.tick < max_ticks and any(th.alive for th in self.threats):
            self.step()
        return self.metrics()

    def step(self):
        t, dt = self.t, C.DT
        nodes, A, W, P = build_graph(self.defenders, self.boxes)
        comps = components(A)

        # connectivity metrics (and Fiedler vector for relay control)
        if self.tick % C.CONN_PERIOD == 0:
            l2, fvec = fiedler(W)
            self._l2, self._fvec, self._comps = l2, fvec, comps
            n = max(1, len(nodes))
            self.series["t"].append(t)
            self.series["l2"].append(l2)
            self.series["lcf"].append(max((len(c) for c in comps), default=0) / n)
            self.series["connected"].append(1.0 if len(comps) <= 1 else 0.0)
            alive_thr = [th for th in self.threats if th.alive]
            if alive_thr:
                fresh = set()
                for a in nodes:
                    for tid, (_, _, ts) in a.tracks.items():
                        if t - ts <= C.TRACK_FRESH:
                            fresh.add(tid)
                self.series["tracked"].append(
                    sum(1 for th in alive_thr if th.tid in fresh) / len(alive_thr))
            else:
                self.series["tracked"].append(1.0)

        # sensing: update own track tables from sensor volumes with 3D LOS
        for a in nodes:
            if a.sensor is None:
                continue
            for th in self.threats:
                if not th.alive:
                    continue
                r = th.p - a.p
                d = np.linalg.norm(r)
                if d > a.s_range:
                    continue
                if a.sensor == "cone":
                    # downward-looking cone about -z
                    cosang = -r[2] / max(d, 1e-6)
                    if cosang < np.cos(a.s_half):
                        continue
                if not los_clear(a.p, th.p, self.boxes):
                    continue
                a.tracks[th.tid] = (
                    th.p + self.rng.normal(0, C.SENSE_NOISE_P, 3),
                    th.v + self.rng.normal(0, C.SENSE_NOISE_V, 3),
                    t,
                )

        # lossy track sharing over links
        idx_pairs = np.argwhere(np.triu(A) > 0)
        for i, j in idx_pairs:
            ai, aj = nodes[i], nodes[j]
            p_link = P[i, j]
            for src, dst in ((ai, aj), (aj, ai)):
                for tid, rec in list(src.tracks.items()):
                    if t - rec[2] > C.TRACK_STALE:
                        continue
                    if tid in dst.tracks and dst.tracks[tid][2] >= rec[2]:
                        continue
                    if self.rng.random() < p_link:
                        dst.tracks[tid] = rec
        for a in nodes:  # prune stale
            a.tracks = {k: r for k, r in a.tracks.items() if t - r[2] <= C.TRACK_STALE}

        # task allocation per connected component
        if self.tick % C.ALLOC_PERIOD == 0:
            for comp in comps:
                members = [nodes[i] for i in comp]
                auction_interceptors(members, t)
                auction_sentinels(members, self.stations, t)

        # defender control
        for a in nodes:
            acc = self._defender_accel(a, nodes, W, comps, t)
            acc += avoidance(a, nodes) + box_repulse(a.p, self.boxes)
            na = np.linalg.norm(acc)
            if na > a.amax:
                acc *= a.amax / na
                na = a.amax
            a.v += acc * dt
            sp = np.linalg.norm(a.v)
            if sp > a.vmax:
                a.v *= a.vmax / sp
                sp = a.vmax
            a.p += a.v * dt
            if a.p[2] < 2.0:
                a.p[2] = 2.0
                a.v[2] = max(0.0, a.v[2])
            if np.isfinite(a.fuel):
                a.fuel -= dt * (sp / a.vmax) ** 2
                if a.fuel <= 0:
                    a.alive = False
                    self.events.append(("death", round(t, 2), a.idx, "fuel"))
            if self.sc["debug"]:
                assert sp <= a.vmax + 1e-6 and na <= a.amax + 1e-6

        # threat control + outcome resolution
        hunters = [a for a in self.defenders if a.alive and a.can_intercept]
        for th in self.threats:
            if not th.alive:
                continue
            acc = self._threat_accel(th, hunters, t) + box_repulse(th.p, self.boxes)
            na = np.linalg.norm(acc)
            if na > C.THREAT["amax"]:
                acc *= C.THREAT["amax"] / na
            th.v += acc * dt
            sp = np.linalg.norm(th.v)
            if sp > C.THREAT["vmax"]:
                th.v *= C.THREAT["vmax"] / sp
            th.p += th.v * dt
            if th.p[2] < 5.0:
                th.p[2] = 5.0
                th.v[2] = max(0.0, th.v[2])
            # intercepted?
            for h in hunters:
                if np.linalg.norm(h.p - th.p) < C.KILL_RADIUS:
                    th.alive = False
                    th.outcome, th.t_out = "killed", t
                    self.events.append(("intercept", round(t, 2), th.tid, h.idx))
                    break
            # leaked?
            if th.alive and np.linalg.norm(th.p - C.ASSET_POS) < C.ASSET_RADIUS:
                th.alive = False
                th.outcome, th.t_out = "leaked", t
                self.events.append(("leak", round(t, 2), th.tid, -1))
            if not th.alive:  # kill confirmation: purge track everywhere
                for a in self.defenders:
                    a.tracks.pop(th.tid, None)
                for a in self.defenders:
                    if a.assign == th.tid:
                        a.assign = None

        # scheduled node-loss events (resilience experiments)
        while self.kill_schedule and t >= self.kill_schedule[0][0]:
            _, k = self.kill_schedule.pop(0)
            pool = [a for a in self.defenders if a.alive]
            for a in self.rng.choice(pool, size=min(k, len(pool)), replace=False):
                a.alive = False
                self.events.append(("death", round(t, 2), a.idx, "attrition"))

        if self.frames is not None and self.tick % 2 == 0:
            self._record(A, nodes)
        self.tick += 1
        self.t = self.tick * C.DT

    # ------------------------------------------------------- role behaviors
    def _defender_accel(self, a, nodes, W, comps, t):
        if a.role == "relay":
            return relay_accel(a, nodes, W, self._fvec, comps,
                               C.RELAY_ALT_BAND, a.cruise)
        if a.role == "sentinel":
            si = a.station if a.station is not None else a.idx % 4
            orbit = 25.0 * np.array([np.cos(0.1 * t + a.idx), np.sin(0.1 * t + a.idx), 0])
            return goto(a.p, a.v, self.stations[si] + orbit, a.cruise)
        # interceptor / generalist
        if a.assign is not None and a.assign in a.tracks:
            p_tr, v_tr, ts = a.tracks[a.assign]
            p_pred = p_tr + v_tr * (self.t - ts)
            return pn_accel(a.p, a.v, p_pred, v_tr, a.vmax)
        return goto(a.p, a.v, a.home, a.cruise)

    def _threat_accel(self, th, hunters, t):
        # head for the asset at cruise altitude, dive when close
        aim = C.ASSET_POS.copy()
        d_xy = np.linalg.norm((th.p - aim)[:2])
        if d_xy > 150:
            level = C.ASSET_POS - th.p
            level[2] = 0.0
            aim = th.p + unit(level) * 100.0
            aim[2] = th.cruise_alt
        v_des = unit(aim - th.p) * C.THREAT["vmax"]
        acc = 1.5 * (v_des - th.v)
        if not self.sc["evasion"]:
            return acc
        # weave perpendicular to the approach direction
        e_to = unit(C.ASSET_POS - th.p)
        e_perp = unit(np.cross(e_to, np.array([0, 0, 1.0])))
        acc += C.THREAT["weave_a"] * np.sin(th.omega * t + th.phase) * e_perp
        acc[2] += 0.5 * C.THREAT["weave_a"] * np.sin(0.7 * th.omega * t + 2 * th.phase)
        # reactive jink away from the nearest closing hunter
        near = None
        best = C.THREAT["jink_range"]
        for h in hunters:
            d = np.linalg.norm(h.p - th.p)
            if d < best:
                best, near = d, h
        if near is not None:
            if t > th.jink_until:
                los = unit(th.p - near.p)
                perp = np.cross(los, self.rng.normal(size=3))
                th.jink_dir = unit(perp)
                th.jink_until = t + 1.5
            acc += C.THREAT["jink_a"] * th.jink_dir
        return acc

    # ------------------------------------------------------------- outputs
    def _record(self, A, nodes):
        edges = [[nodes[i].idx, nodes[j].idx] for i, j in np.argwhere(np.triu(A) > 0)]
        self.frames.append({
            "t": round(self.t, 2),
            "def": [[round(float(x), 1) for x in a.p] + [1 if a.alive else 0]
                    for a in self.defenders],
            "thr": [[round(float(x), 1) for x in th.p] + [1 if th.alive else 0]
                    for th in self.threats],
            "edges": edges,
            "l2": round(float(self._l2), 3),
        })

    def metrics(self):
        killed = [th for th in self.threats if th.outcome == "killed"]
        leaked = [th for th in self.threats if th.outcome == "leaked"]
        s = self.series
        return {
            "team": self.sc["team"] if isinstance(self.sc["team"], str) else "custom",
            "n_threats": self.sc["n_threats"],
            "seed": self.sc["seed"],
            "killed": len(killed),
            "leaked": len(leaked),
            "survived": sum(1 for th in self.threats if th.alive),
            "interception_rate": len(killed) / max(1, len(self.threats)),
            "tti_mean": float(np.mean([th.t_out for th in killed])) if killed else None,
            "uptime": float(np.mean(s["connected"])) if s["connected"] else 0.0,
            "lcf_mean": float(np.mean(s["lcf"])) if s["lcf"] else 0.0,
            "l2_mean": float(np.mean(s["l2"])) if s["l2"] else 0.0,
            "tracked_mean": float(np.mean(s["tracked"])) if s["tracked"] else 0.0,
            "defender_losses": sum(1 for a in self.defenders if not a.alive),
            "t_end": self.t,
            "events": self.events,
        }
