# Counter-Swarm

A 3D simulation of a heterogeneous drone team defending a site against an evasive
attacking swarm. It studies one question: when a team's own motion keeps changing
what it can see and who it can talk to, what does each specialist role contribute?

![Demo engagement](results/demo.gif)

*16 defenders against 10 attackers flying low among buildings. Sentinels are amber
diamonds, interceptors blue arrows, relays green circles, and attackers red triangles.
Grey lines are radio links and crosses mark intercepts. [Full-resolution video](results/demo.mp4).*

## Overview

Three subproblems that are usually studied separately are simulated together, in
closed loop:

| Subsystem | Model | Effect |
|---|---|---|
| Sensing | Cone and sphere sensors with 3D line-of-sight occlusion by buildings | Low-flying attackers drop in and out of view |
| Communication | Range- and line-of-sight-limited radio links with distance-dependent loss | The network topology changes as drones move |
| Allocation | Consensus auctions (CBBA, bundle size 1) run within each connected component | A disconnected drone cannot take part in coordination |

The defenders have three roles with different flight characteristics:

- **Sentinels**: slow, high-altitude, carry the wide-area sensors.
- **Interceptors**: fast, pursue targets with 3D proportional navigation.
- **Relays**: follow the gradient of the network's algebraic connectivity (λ₂) to keep
  the team connected.

An interceptor that chases a target far from the team can break the network that
supplies its target updates, and the relays try to repair it during the engagement.

## Results

All conditions use 16 defenders and 10 random seeds per data point. Baselines are a
no-relay team (4 sentinels, 12 interceptors) and a homogeneous team (16 identical
generalist drones). Time to intercept (TTI) is the time from the start of the episode
to the kill, averaged over the attackers that were killed; it is dominated by approach
geometry (attackers spawn 750–900 m out), so differences between teams are the
meaningful part. Significance below is Welch's t-test over the 10 seeds.

![E1 scaling results](results/e1_scaling.png)

- **Sentinels detect earlier, and that is where the speed-up comes from.** The
  heterogeneous team's mean TTI is lower than the homogeneous team's at every attack
  size (20.1–22.9 s vs. 22.4–23.9 s). The gap is 3.0 s and 1.8 s at 4 and 8 attackers
  (p = 0.006 and p < 0.001) and 0.7–1.0 s at 12 and 16, where it is not significant
  (p = 0.30 and 0.16). The heterogeneous team first detects each attacker 2.6–3.1 s
  sooner (p < 0.001 at every size), while its time from first detection to kill is
  no shorter, and is longer at 12 and 16 attackers (by 2.0 and 1.7 s, p < 0.01). It
  also holds a fresh track on more of the live attackers (0.55 vs. 0.43 at 8
  attackers; significant at 8 attackers and above).
- **Relays raise λ₂, but not uptime or kills, against the no-relay team.** With relays,
  mean algebraic connectivity is 2.1–2.3× that of the no-relay team. Part of this is
  built into the metric: link weights scale with radio range, and relays carry longer
  radios than interceptors. Mesh uptime (fraction of time fully connected) is not
  measurably different (−0.04 to +0.05, p ≥ 0.17), and the largest connected fraction
  is 0.98–0.99 for both. The no-relay team's interception rate is equal or higher at
  every size (0.88 vs. 0.80 at 16 attackers) but the difference is not significant at
  10 seeds (p ≥ 0.25). The homogeneous team's λ₂ (0.45–0.83) lies between the two and
  exceeds the relay team's at 16 attackers; its uptime is the lowest at 4 and 12
  attackers (0.70 and 0.67 vs. 0.83 and 0.81 for the relay team).

![E2 resilience results](results/e2_resilience.png)

- **After losing 3 of 16 defenders (19%) at 15 s**, just before the first intercept
  of any run (earliest 15.4 s, median 17.7 s), the relay team's post-loss λ₂ is 3.8×
  the no-relay team's (0.28 vs. 0.07, p = 0.001) and about equal to the homogeneous
  team's (0.30). Its post-loss uptime (0.74) is similar to the no-relay team's (0.71,
  p = 0.78) and higher than the homogeneous team's (0.48, p = 0.011). Post-loss
  interception rates are indistinguishable (0.96–0.97).

In short, dedicated sentinels measurably improve detection and therefore time to
intercept. At this scale, the relays' benefit shows up only in λ₂; they do not
measurably improve connectivity uptime or interception against a team that spends the
same airframes on interceptors.

## Quickstart

Requires Python 3 with NumPy and Matplotlib (`requirements.txt`); the tests also
need pytest (`requirements-dev.txt`).

```bash
pip install -r requirements-dev.txt
python -m pytest -q         # unit tests
python run_sanity.py        # verification checks; run first
python run_experiments.py   # experiments E1 and E2 -> results/results.json (~10 min)
python make_plots.py        # figures and summary table
python export_run.py        # record a demo run -> viewer/data.js
```

To re-render the demo GIF, video, and screenshot from the viewer (needs Node,
Playwright, and ffmpeg), run `node tools/render_media.mjs`.

`run_sanity.py` exits non-zero if any check fails. It checks that a single
interceptor converges on straight and evasive targets; that speeds and accelerations
recomputed from the recorded positions stay within each role's limits (except where
the hard altitude floor stops a descent, which is counted and excluded); that swapping
4 interceptors for 4 relays raises λ₂ on every one of 10 paired seeds and raises mean
uptime; and that buildings lower track coverage of low-flying attackers on average
over 10 paired seeds. The last two are direction checks, not significance tests; the
occlusion effect is small (about 1 percentage point).

## 3D viewer

![Viewer screenshot](results/demo_still.png)

Serve the viewer with `python -m http.server --directory viewer` and open
`http://localhost:8000`. By default the camera follows the engagement; drag to orbit
and scroll to zoom, which switches to manual control. The control bar has play,
pause, speed, and a timeline. The overlay shows the intercept count and the network's
algebraic connectivity over time.

## How it works

- **Dynamics**: each aircraft is a 3D point mass with role-specific speed and
  acceleration limits, integrated at 50 ms steps. Interceptor fuel use scales with
  speed squared, but fuel does not bind in these engagements, which last 19.5–38.7 s
  (the lowest remaining fuel in any run is 72%).
- **Guidance**: interceptors use vector proportional navigation,
  `a = N (Ω × v)` with `Ω = (r × v_rel) / |r|²`. A kill occurs within 6 m.
- **Allocation**: once per second, each connected group auctions the fresh tracks its
  members hold. Bids are estimated time-to-go, gated by fuel, with hysteresis to
  prevent constant reassignment. A second auction assigns sentinels to lookout stations near the
  threats.
- **Relay control**: gradient ascent on λ₂ using the Fiedler vector. Each relay moves
  toward the weakest point in the network, or bridges the gap if the network has
  already split.
- **Attackers**: spawn 750–900 m out in clusters, fly at 15–35 m altitude among the
  buildings, weave, and evade any interceptor within 130 m.

## Repository layout

```
sim/                 simulation core (config, world, comms, guidance, allocation, engine)
tests/               unit tests (pytest)
run_sanity.py        verification checks
run_experiments.py   experiments E1 and E2
make_plots.py        figures and summary table
export_run.py        demo recording for the viewer
viewer/              Three.js playback viewer and recorded demo
tools/               render_media.mjs: renders the demo GIF, video, and screenshot
results/             experiment data, figures, demo media
paper/               LaTeX paper and figures
docs/design.md       design decisions
```

## Paper

[`paper/paper.tex`](paper/paper.tex) covers the problem, related work, method,
experiments, results, and limitations. The folder is self-contained and compiles
as-is (for example, on Overleaf).
