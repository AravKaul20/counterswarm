"""Communication graph: range- and LOS-limited lossy links, algebraic connectivity."""
import numpy as np
from .config import SIGMA_FRAC, P_FLOOR, TRACK_STALE
from .world import los_clear


def build_graph(agents, boxes):
    """Weighted comm graph over alive defenders.

    Returns (nodes, A, W, P): adjacency (0/1), Laplacian edge weights, and
    per-link delivery probabilities, all n x n symmetric.
    """
    nodes = [a for a in agents if a.alive]
    n = len(nodes)
    A = np.zeros((n, n))
    W = np.zeros((n, n))
    P = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            R = min(nodes[i].comm, nodes[j].comm)
            d = np.linalg.norm(nodes[i].p - nodes[j].p)
            if d < R and los_clear(nodes[i].p, nodes[j].p, boxes):
                A[i, j] = A[j, i] = 1.0
                W[i, j] = W[j, i] = np.exp(-(d / (SIGMA_FRAC * R)) ** 2)
                P[i, j] = P[j, i] = max(P_FLOOR, 1.0 - (d / R) ** 4)
    return nodes, A, W, P


def fiedler(W):
    """(lambda2, Fiedler vector) of the weighted Laplacian. lambda2=0 if disconnected."""
    n = W.shape[0]
    if n < 2:
        return 0.0, np.zeros(n)
    L = np.diag(W.sum(axis=1)) - W
    vals, vecs = np.linalg.eigh(L)
    return max(0.0, vals[1]), vecs[:, 1]


def components(A):
    """List of index lists, one per connected component."""
    n = A.shape[0]
    seen = [False] * n
    comps = []
    for s in range(n):
        if seen[s]:
            continue
        stack, comp = [s], []
        seen[s] = True
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in np.nonzero(A[u])[0]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(int(v))
        comps.append(comp)
    return comps


def share_tracks(nodes, A, P, t, rng):
    """Lossy track exchange over every link; each (link, direction, track) is
    delivered with probability P[i, j]. Nodes send what they held at the start
    of the call, so a track moves at most one hop per call (per tick).
    Mutates the nodes' track tables."""
    sent = [dict(a.tracks) for a in nodes]  # pre-exchange snapshot
    idx_pairs = np.argwhere(np.triu(A) > 0)
    for i, j in idx_pairs:
        p_link = P[i, j]
        for s, dst in ((i, nodes[j]), (j, nodes[i])):
            for tid, rec in sent[s].items():
                if t - rec[2] > TRACK_STALE:
                    continue
                if tid in dst.tracks and dst.tracks[tid][2] >= rec[2]:
                    continue
                if rng.random() < p_link:
                    dst.tracks[tid] = rec
