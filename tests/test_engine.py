import numpy as np
from sim import Simulation
from sim import config as C


def alive_count(sim):
    return sum(a.alive for a in sim.defenders)


def test_fiedler_vector_matches_alive_nodes_after_loss():
    sim = Simulation(dict(team="full", n_threats=4, seed=3))
    for _ in range(C.CONN_PERIOD + 1):
        sim.step()
    assert sim.tick % C.CONN_PERIOD != 0
    sim.defenders[0].alive = False
    sim.defenders[5].alive = False
    for _ in range(C.CONN_PERIOD):
        sim.step()
        assert len(sim._fvec) == alive_count(sim)


def test_first_detection_time_is_recorded_once():
    sim = Simulation(dict(team={"sentinel": 1}, n_threats=1, seed=0))
    sentinel, threat = sim.defenders[0], sim.threats[0]
    sim.boxes = []
    threat.p = sentinel.p + np.array([0.0, 0.0, -100.0])  # inside the down-cone
    assert threat.t_detect is None
    sim.step()
    assert threat.t_detect == 0.0
    sim.step()
    sim.step()
    assert threat.t_detect == 0.0


def test_undetected_threat_has_no_detection_time():
    sim = Simulation(dict(team={"sentinel": 1}, n_threats=1, seed=0))
    sim.threats[0].p = np.array([5000.0, 0.0, 50.0])
    sim.step()
    assert sim.threats[0].t_detect is None


def test_floor_contact_is_counted():
    sim = Simulation(dict(team={"interceptor": 1}, n_threats=1, seed=0))
    a = sim.defenders[0]
    a.p = np.array([0.0, 0.0, 2.5])
    a.v = np.array([0.0, 0.0, -20.0])
    sim.step()
    assert a.p[2] == 2.0 and a.v[2] == 0.0
    assert sim.floor_contacts == 1
