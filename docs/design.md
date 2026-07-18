# Design: Heterogeneous 3D Counter-Drone Swarm Defense Simulation

Date: 2026-07-17

## Research gap

**Heterogeneous role reallocation under partial 3D observability and dynamic connectivity.**
The component problems each have mature literature — consensus-based task allocation
(CBBA and descendants), 3D proportional-navigation interception, and connectivity
maintenance via algebraic-connectivity control — but they are almost always studied in
isolation, with the other subsystems idealized (global information, static topology, or
homogeneous teams). Here the three are *coupled in closed loop*: allocation quality
depends on which tracks reach which agents over a lossy, occlusion-limited mesh;
mesh topology depends on where relays fly; sensing coverage depends on sentinel-station
allocation; and interceptor sprints physically reshape the graph. The simulation
quantifies the cost of that coupling and the value of dedicated relay/sensing roles
against equal-budget baselines.

## Scope decisions (made per user's process instructions)

- **Roles: sentinel / interceptor / relay only.** The optional 4th (EW/deception) role
  is omitted — it would add a jamming model without deepening the allocation/connectivity
  core. Baseline "generalist" role exists only for the homogeneous comparison.
- **Allocation: consensus greedy auction = CBBA with bundle size |b|=1**, capability-gated
  bids, run per connected component each 1 s, with hysteresis to prevent churn. Full CBBA
  bundles add complexity without changing the phenomenon under study (single-assignment
  pursuit tasks).
- **Interceptors are reusable effectors** (net/hard-kill with re-attack); resource limits
  come from fuel, not one-shot expenditure. This makes re-tasking after kills a real
  allocation problem and lets interception rate scale past interceptor count.
- **Relay control: gradient ascent on λ₂ (Fiedler value) of the weighted comms Laplacian**
  (Zavlanos-Pappas-style), with a component-bridging fallback when the graph is split.
  Directly extends the prior 2D adaptive-topology work into 3D.
- **Dynamics: point-mass with per-role speed/accel limits** (per user requirement; 6DOF
  is over-engineering).
- **Occlusion: segment-vs-AABB line-of-sight against buildings** near the defended asset;
  threats fly low among buildings (terrain masking), sentinels look down from altitude —
  so 3D LOS geometry materially affects detection and comms.
- **Guidance: true 3D vector PN**, a = N (Ω × v), Ω = (r × v_rel)/|r|², on coasted track
  predictions — not a planar law with altitude bolted on.
- **Viz: Three.js playback viewer** (records run to JSON, renders locally with CDN
  three.js) + matplotlib for metric plots. Sim stays in Python for experiment throughput.

## Scenario

Threats (configurable count, clustered azimuths, weave + reactive jink evasion) attack a
protected asset at the origin. Defenders: 4 sentinels (high-alt cone sensors),
8 interceptors (fast, fuel-limited, short-range seekers), 4 relays. Threat leaks if it
reaches the asset sphere; intercepted if an interceptor closes within kill radius.

## Evaluation

- Conditions: **full** (4S+8I+4R) vs **no-relay equal budget** (4S+12I) vs
  **homogeneous equal budget** (16 generalists).
- E1 scaling: threat count ∈ {4, 8, 12, 16} × 5 seeds → interception rate, mean
  time-to-intercept, mesh uptime (fraction of ticks fully connected), mean largest-component
  fraction, mean λ₂, track coverage.
- E2 node loss: 8 threats, kill 3 random defenders at t=40 s → connectivity recovery.
- Self-verification gate before experiments: 1v1 convergence, evasive 1v1, relay-count
  sweep monotonicity, occlusion sanity, speed/accel bound asserts.

## Module map

`sim/config.py` role profiles & constants · `sim/world.py` buildings + LOS ·
`sim/comms.py` graph, λ₂, components, loss · `sim/guidance.py` PN, goto, relay gradient,
threat evasion · `sim/allocation.py` auctions · `sim/engine.py` entities + loop + metrics ·
`run_sanity.py` verification gate · `run_experiments.py` E1/E2 + plots ·
`export_run.py` demo recording → `viewer/` Three.js playback · `paper/paper.tex` ·
`OUTREACH.md`.
