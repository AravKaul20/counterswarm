"""Consensus greedy auction (CBBA with bundle size 1) run per connected component.

Bids are capability-gated (role, fuel) and scored by estimated time-to-go from
3D engagement geometry. Hysteresis discounts the incumbent assignment's cost to
prevent churn. Sentinels are allocated to coverage stations by a second auction
weighted by threat density per sector.
"""
import numpy as np
from .config import TRACK_FRESH, SENTINEL_STATION_R, SENTINEL_STATION_ALT

FUEL_GATE = 20.0  # interceptors at or below this fuel do not bid


def t_go(p_i, vmax, p_t, v_t):
    """Smallest positive t with |p_t + v_t t - p_i| = vmax t (constant-bearing
    intercept time); falls back to range/vmax if no closed-form solution."""
    r = p_t - p_i
    a = v_t @ v_t - vmax * vmax
    b = 2.0 * (r @ v_t)
    c = r @ r
    if abs(a) < 1e-9:
        return c / max(-b, 1e-6) if b < 0 else np.linalg.norm(r) / vmax
    disc = b * b - 4 * a * c
    if disc < 0:
        return 1.5 * np.linalg.norm(r) / vmax
    sq = np.sqrt(disc)
    ts = [t for t in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)) if t > 0]
    return min(ts) if ts else 1.5 * np.linalg.norm(r) / vmax


def fuse_tracks(members, t):
    """Union of members' track tables (newest record wins), fresh only."""
    fused = {}
    for m in members:
        for tid, (p, v, ts) in m.tracks.items():
            if t - ts <= TRACK_FRESH and (tid not in fused or ts > fused[tid][2]):
                fused[tid] = (p, v, ts)
    return fused


def auction_interceptors(members, t):
    """Assign each hunter in the component at most one threat track; double-team
    with surplus hunters. Mutates .assign on the bidders."""
    bidders = []
    for m in members:
        if not (m.can_intercept and m.alive):
            continue
        if m.fuel > FUEL_GATE:
            bidders.append(m)
        else:
            m.assign = None  # too little fuel to bid: release the task, fly home
    fused = fuse_tracks(members, t)
    if not bidders:
        return
    if not fused:
        for b in bidders:
            b.assign = None
        return
    bids = []
    for b in bidders:
        for tid, (p, v, ts) in fused.items():
            cost = t_go(b.p, b.vmax, p + v * (t - ts), v)
            if b.assign == tid:
                cost *= 0.8  # hysteresis: incumbent keeps task on near-ties
            bids.append((cost, b, tid))
    bids.sort(key=lambda x: x[0])
    taken_task, taken_bidder = set(), set()
    for cost, b, tid in bids:
        if id(b) in taken_bidder or tid in taken_task:
            continue
        b.assign = tid
        taken_bidder.add(id(b))
        taken_task.add(tid)
    # surplus hunters double-team their cheapest task
    for cost, b, tid in bids:
        if id(b) not in taken_bidder:
            b.assign = tid
            taken_bidder.add(id(b))


def station_points(k):
    az = np.linspace(0, 2 * np.pi, k, endpoint=False)
    return [np.array([SENTINEL_STATION_R * np.cos(a),
                      SENTINEL_STATION_R * np.sin(a),
                      SENTINEL_STATION_ALT]) for a in az]


def auction_sentinels(members, stations, t):
    """Greedy sentinel->station assignment maximizing (threat weight)/(travel).
    Station weight = 1 + fresh threat tracks whose azimuth falls in its sector."""
    sentinels = [m for m in members if m.role == "sentinel" and m.alive]
    if not sentinels:
        return
    fused = fuse_tracks(members, t)
    k = len(stations)
    weights = np.ones(k)
    for tid, (p, v, ts) in fused.items():
        az = np.arctan2(p[1], p[0]) % (2 * np.pi)
        sector = int(round(az / (2 * np.pi / k))) % k
        weights[sector] += 1.0
    bids = []
    for s in sentinels:
        for si in range(k):
            travel = np.linalg.norm(stations[si] - s.p)
            if s.station == si:
                travel *= 0.8  # hysteresis
            bids.append((travel / weights[si], s, si))
    bids.sort(key=lambda x: x[0])
    taken_s, taken_st = set(), set()
    for cost, s, si in bids:
        if id(s) in taken_s or si in taken_st:
            continue
        s.station = si
        taken_s.add(id(s))
        taken_st.add(si)
