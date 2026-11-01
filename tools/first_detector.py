"""Which role first detects each attacker, and do sentinels change station?

Replays the E1 full-team runs with two read-only spies (they consume no random
numbers, so the runs match results/results.json) and prints:
  - the role of the defender whose sensor first saw each attacker;
  - how many times the sentinel station auction moved a sentinel.
Usage: python tools/first_detector.py   (about 2 minutes)
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import sim.engine as E  # noqa: E402
from sim import Simulation  # noqa: E402

los_hits = []
_los_clear = E.los_clear


def los_spy(p, q, boxes):
    clear = _los_clear(p, q, boxes)
    if clear:
        los_hits.append((id(p), id(q)))
    return clear


moves = Counter()
_auction = E.auction_sentinels


def auction_spy(members, stations, t):
    before = {id(m): m.station for m in members if m.role == "sentinel"}
    _auction(members, stations, t)
    for m in members:
        if m.role != "sentinel":
            continue
        if before[id(m)] is None:
            moves["first assignment = spawn station" if m.station == m.idx % 4
                  else "first assignment != spawn station"] += 1
        elif m.station != before[id(m)]:
            moves["reassignments"] += 1


E.los_clear = los_spy           # sensing calls only; comms imports its own copy
E.auction_sentinels = auction_spy

R = json.load(open(ROOT / "results" / "results.json"))
first = Counter()
for ref in (m for m in R["E1"] if m["team"] == "full"):
    s = Simulation(dict(team="full", n_threats=ref["n_threats"], seed=ref["seed"]))
    while s.tick < int(E.C.SIM_TIME / E.C.DT) and any(th.alive for th in s.threats):
        undetected = [th for th in s.threats if th.t_detect is None]
        los_hits.clear()
        s.step()
        for th in undetected:
            if th.t_detect is not None:
                pid = next(p for p, q in los_hits if q == id(th.p))
                first[next(a.role for a in s.defenders if id(a.p) == pid)] += 1
    assert s.metrics()["tti_mean"] == ref["tti_mean"], "replay differs from results.json"

print(f"E1 full team, {sum(first.values())} attackers: first detector by role {dict(first)}")
print(f"sentinel station auction: {dict(moves)}")
