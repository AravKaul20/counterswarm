"""Motion primitives: 3D proportional navigation, waypoint PD control,
relay lambda2-gradient repositioning, and intra-swarm collision avoidance."""
import numpy as np
from .config import PN_GAIN, SIGMA_FRAC


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else np.zeros(3)


def pn_accel(p_i, v_i, p_t, v_t, vmax):
    """True 3D vector PN: a = N (Omega x v_i), Omega = (r x v_rel)/|r|^2,
    plus a longitudinal term that drives speed to vmax (sprint)."""
    r = p_t - p_i
    d = np.linalg.norm(r)
    if d < 1e-6:
        return np.zeros(3)
    v_rel = v_t - v_i
    omega = np.cross(r, v_rel) / (d * d)
    a_lat = PN_GAIN * np.cross(omega, v_i)
    speed = np.linalg.norm(v_i)
    if speed < 1.0:
        # PN undefined at rest: accelerate straight at the target
        return 30.0 * unit(r)
    a_long = 2.0 * (vmax - speed) * unit(v_i)
    return a_lat + a_long


def goto(p, v, target, cruise):
    """PD acceleration toward a point, arriving at ~cruise speed."""
    r = target - p
    d = np.linalg.norm(r)
    v_des = unit(r) * min(cruise, 0.6 * d)
    return 1.5 * (v_des - v)


def relay_accel(relay, nodes, W, fvec, comps, alt_band, cruise):
    """Reposition a relay to increase lambda2 (gradient ascent on the Fiedler
    value), or bridge toward the nearest foreign component if the graph is split.

    d(lambda2)/dp_i = sum_j (f_i - f_j)^2 * dw/dd * (p_i - p_j)/d
    with w = exp(-(d/sigma)^2)  =>  dw/dd = -2 d w / sigma^2.
    """
    idx = nodes.index(relay)
    n = len(nodes)
    if len(comps) > 1:
        # bridge: midpoint between my component and the closest node outside it
        mine = next(c for c in comps if idx in c)
        best, target = np.inf, None
        for i in mine:
            for j in range(n):
                if j in mine:
                    continue
                d = np.linalg.norm(nodes[i].p - nodes[j].p)
                if d < best:
                    best = d
                    target = 0.5 * (nodes[i].p + nodes[j].p)
        a = goto(relay.p, relay.v, target, relay.vmax) if target is not None else np.zeros(3)
    else:
        grad = np.zeros(3)
        for j in range(n):
            w = W[idx, j]
            if w <= 0.0 or j == idx:
                continue
            rij = relay.p - nodes[j].p
            d = np.linalg.norm(rij)
            R = min(relay.comm, nodes[j].comm)
            sigma = SIGMA_FRAC * R
            dw = -2.0 * d * w / sigma ** 2
            grad += (fvec[idx] - fvec[j]) ** 2 * dw * rij / max(d, 1e-6)
        g = np.linalg.norm(grad)
        if g > 1e-8:
            a = goto(relay.p, relay.v, relay.p + 60.0 * grad / g, relay.vmax)
        else:
            # flat gradient: drift toward swarm centroid to stay useful
            cen = np.mean([nd.p for nd in nodes], axis=0)
            a = goto(relay.p, relay.v, cen, 0.5 * cruise)
    # hold altitude band
    lo, hi = alt_band
    if relay.p[2] < lo:
        a[2] += 3.0 * (lo - relay.p[2]) - 2.0 * relay.v[2]
    elif relay.p[2] > hi:
        a[2] += 3.0 * (hi - relay.p[2]) - 2.0 * relay.v[2]
    return a


def avoidance(agent, others, d_min=15.0, k=8.0):
    """Pairwise repulsive acceleration below separation d_min."""
    a = np.zeros(3)
    for o in others:
        if o is agent or not o.alive:
            continue
        r = agent.p - o.p
        d = np.linalg.norm(r)
        if 1e-6 < d < d_min:
            a += k * (d_min - d) / d_min * r / d
    # ground avoidance
    if agent.p[2] < 8.0:
        a[2] += 4.0 * (8.0 - agent.p[2]) - 2.0 * min(0.0, agent.v[2])
    return a
