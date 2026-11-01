import numpy as np
import pytest
from sim.comms import fiedler, components, share_tracks
from sim.engine import Agent


def path_weights(n):
    W = np.zeros((n, n))
    for i in range(n - 1):
        W[i, i + 1] = W[i + 1, i] = 1.0
    return W


@pytest.mark.parametrize("n", [3, 4, 6])
def test_fiedler_value_of_path_graph(n):
    l2, f = fiedler(path_weights(n))
    assert l2 == pytest.approx(2.0 * (1.0 - np.cos(np.pi / n)))
    # Fiedler vector of a path is monotone along the path and sums to zero
    d = np.diff(f)
    assert np.all(d > 0) or np.all(d < 0)
    assert f.sum() == pytest.approx(0.0, abs=1e-9)


def test_fiedler_disconnected_graph_is_zero():
    W = np.zeros((4, 4))
    W[0, 1] = W[1, 0] = 1.0
    W[2, 3] = W[3, 2] = 1.0
    assert fiedler(W)[0] == pytest.approx(0.0, abs=1e-12)


def test_components():
    A = np.zeros((5, 5))
    A[0, 1] = A[1, 0] = 1.0
    A[2, 3] = A[3, 2] = 1.0
    comps = sorted(sorted(c) for c in components(A))
    assert comps == [[0, 1], [2, 3], [4]]


def line_nodes(n):
    nodes = [Agent(i, "relay", [100.0 * i, 0.0, 80.0]) for i in range(n)]
    return nodes, path_weights(n), path_weights(n)


def test_track_moves_one_hop_per_tick():
    nodes, A, P = line_nodes(4)  # delivery probability 1 on every link
    nodes[0].tracks[7] = (np.zeros(3), np.zeros(3), 0.0)
    rng = np.random.default_rng(0)
    for tick in range(1, 4):
        share_tracks(nodes, A, P, 0.0, rng)
        holders = [i for i, a in enumerate(nodes) if 7 in a.tracks]
        assert holders == list(range(tick + 1))


def test_track_moves_one_hop_regardless_of_node_order():
    nodes, A, P = line_nodes(4)
    nodes[3].tracks[7] = (np.zeros(3), np.zeros(3), 0.0)
    share_tracks(nodes, A, P, 0.0, np.random.default_rng(0))
    assert [i for i, a in enumerate(nodes) if 7 in a.tracks] == [2, 3]


def test_newer_record_wins_and_stale_not_sent():
    nodes, A, P = line_nodes(2)
    nodes[0].tracks[1] = (np.ones(3), np.zeros(3), 5.0)
    nodes[1].tracks[1] = (np.zeros(3), np.zeros(3), 3.0)
    nodes[0].tracks[2] = (np.zeros(3), np.zeros(3), 0.0)  # older than TRACK_STALE at t=6
    share_tracks(nodes, A, P, 6.0, np.random.default_rng(0))
    assert nodes[1].tracks[1][2] == 5.0
    assert 2 not in nodes[1].tracks
    assert nodes[0].tracks[1][2] == 5.0
