import numpy as np
import pytest
from sim.allocation import t_go, auction_interceptors
from sim.engine import Agent


def test_t_go_stationary_target_is_range_over_speed():
    assert t_go(np.zeros(3), 10.0, np.array([100.0, 0, 0]), np.zeros(3)) == pytest.approx(10.0)


def test_t_go_receding_and_closing_targets():
    p_t = np.array([100.0, 0, 0])
    assert t_go(np.zeros(3), 10.0, p_t, np.array([5.0, 0, 0])) == pytest.approx(20.0)
    assert t_go(np.zeros(3), 10.0, p_t, np.array([-5.0, 0, 0])) == pytest.approx(100.0 / 15.0)


def test_t_go_satisfies_constant_bearing_condition():
    p_i, vmax = np.array([0.0, 0.0, 50.0]), 40.0
    p_t, v_t = np.array([300.0, 200.0, 20.0]), np.array([-20.0, 5.0, 0.0])
    t = t_go(p_i, vmax, p_t, v_t)
    assert t > 0
    assert np.linalg.norm(p_t + v_t * t - p_i) == pytest.approx(vmax * t)


def test_t_go_unreachable_target_falls_back():
    # target runs away faster than the interceptor can fly
    p_t = np.array([100.0, 0, 0])
    assert t_go(np.zeros(3), 10.0, p_t, np.array([20.0, 0, 0])) == pytest.approx(15.0)


def hunter(idx, x, tracks=None):
    a = Agent(idx, "interceptor", [x, 0.0, 50.0])
    a.tracks = dict(tracks or {})
    return a


def track(x, ts=0.0):
    return (np.array([x, 0.0, 30.0]), np.zeros(3), ts)


def test_auction_assigns_distinct_tasks_when_tasks_suffice():
    tracks = {k: track(100.0 * k) for k in range(5)}
    hs = [hunter(i, 100.0 * i + 10, tracks) for i in range(3)]
    auction_interceptors(hs, 0.0)
    assigned = [h.assign for h in hs]
    assert None not in assigned
    assert len(set(assigned)) == len(assigned)
    # each hunter takes the track it is closest to
    assert assigned == [0, 1, 2]


def test_auction_surplus_hunters_double_team_their_cheapest_task():
    tracks = {0: track(0.0), 1: track(1000.0)}
    hs = [hunter(0, 20.0, tracks), hunter(1, 990.0, tracks),
          hunter(2, 60.0, tracks), hunter(3, 900.0, tracks)]
    auction_interceptors(hs, 0.0)
    assert {hs[0].assign, hs[1].assign} == {0, 1}
    assert hs[2].assign == 0
    assert hs[3].assign == 1


def test_auction_ignores_stale_tracks():
    tracks = {0: track(0.0, ts=0.0)}
    h = hunter(0, 10.0, tracks)
    auction_interceptors([h], 10.0)  # track is 10 s old, beyond TRACK_FRESH
    assert h.assign is None


def test_low_fuel_interceptor_drops_stale_assignment():
    tracks = {0: track(0.0)}
    h = hunter(0, 10.0, tracks)
    h.assign = 0
    h.fuel = 10.0  # below the bid gate
    auction_interceptors([h], 0.0)
    assert h.assign is None


def test_low_fuel_interceptor_released_while_others_bid():
    tracks = {0: track(0.0)}
    low, ok = hunter(0, 10.0, tracks), hunter(1, 50.0, tracks)
    low.assign, low.fuel = 0, 10.0
    auction_interceptors([low, ok], 0.0)
    assert low.assign is None
    assert ok.assign == 0
