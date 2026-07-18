"""Static world: building obstacles near the asset and 3D line-of-sight tests."""
import numpy as np


def make_buildings(rng):
    """Axis-aligned boxes ((lo, hi) corners) ringing the defended asset."""
    boxes = []
    for _ in range(10):
        az = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(60, 350)
        cx, cy = r * np.cos(az), r * np.sin(az)
        wx, wy = rng.uniform(30, 60, size=2)
        h = rng.uniform(50, 130)
        lo = np.array([cx - wx / 2, cy - wy / 2, 0.0])
        hi = np.array([cx + wx / 2, cy + wy / 2, h])
        boxes.append((lo, hi))
    return boxes


def clear_point(p, boxes, clearance=20.0):
    """Lift a waypoint above any building it falls inside."""
    p = np.array(p, dtype=float)
    for lo, hi in boxes:
        if np.all(p[:2] > lo[:2] - 10) and np.all(p[:2] < hi[:2] + 10) and p[2] < hi[2] + clearance:
            p[2] = hi[2] + clearance
    return p


def box_repulse(p, boxes, margin=10.0, k=8.0):
    """Potential-field push out of inflated buildings (shortest-exit axis)."""
    a = np.zeros(3)
    for lo, hi in boxes:
        ilo, ihi = lo - margin, hi + margin
        ihi = ihi.copy()
        if np.all(p > ilo) and np.all(p < ihi):
            # penetration depth along each face; exit through the cheapest one
            exits = [(p[0] - ilo[0], np.array([-1, 0, 0])), (ihi[0] - p[0], np.array([1, 0, 0])),
                     (p[1] - ilo[1], np.array([0, -1, 0])), (ihi[1] - p[1], np.array([0, 1, 0])),
                     (ihi[2] - p[2], np.array([0, 0, 1]))]
            depth, direction = min(exits, key=lambda e: e[0])
            a += k * (1.0 + 0.2 * (margin - min(depth, margin))) * direction
    return a


def los_clear(p, q, boxes):
    """True if the segment p->q intersects no box (slab method)."""
    d = q - p
    for lo, hi in boxes:
        tmin, tmax = 0.0, 1.0
        hit = True
        for k in range(3):
            if abs(d[k]) < 1e-9:
                if p[k] < lo[k] or p[k] > hi[k]:
                    hit = False
                    break
            else:
                t1 = (lo[k] - p[k]) / d[k]
                t2 = (hi[k] - p[k]) / d[k]
                if t1 > t2:
                    t1, t2 = t2, t1
                tmin = max(tmin, t1)
                tmax = min(tmax, t2)
                if tmin > tmax:
                    hit = False
                    break
        if hit:
            return False
    return True
