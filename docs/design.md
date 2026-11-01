# Design

## Research question

How should a heterogeneous drone team allocate roles when it has only partial 3D
observability and its communication network changes as it moves?

Consensus-based task allocation (CBBA and its variants), 3D proportional-navigation
interception, and connectivity maintenance via algebraic connectivity each have a
mature literature. They are usually studied in isolation, with the other subsystems
idealized (global information, static topology, or identical agents). Here they are
coupled in closed loop:

- Allocation depends on which tracks reach which agents over a lossy, occlusion-limited
  network.
- Network topology depends on where the relays fly.
- Sensor coverage depends on where the sentinels are stationed.
- Interceptor pursuits physically reshape the network.

The simulation measures the cost of this coupling and the value of dedicated relay and
sensing roles against equal-size baselines.

## Design decisions

- **Roles: sentinel, interceptor, relay.** An electronic-warfare role was left out; it
  would add a jamming model without deepening the allocation and connectivity
  questions. A "generalist" role exists only for the homogeneous baseline.
- **Allocation: CBBA with bundle size 1.** Bids are capability-gated, auctions run
  within each connected component every second, and hysteresis prevents constant
  reassignment. Larger bundles add complexity without changing the behavior under
  study, since each pursuit is a single-assignment task.
- **Reusable interceptors.** Interceptors can re-attack after a kill instead of being
  one-shot. This makes re-tasking a real allocation problem and lets the interception
  count exceed the number of interceptors. Fuel is modeled (drain scales with speed
  squared, and interceptors below a fuel gate stop bidding and fly home), but it does
  not bind in the current engagements (19.5–38.7 s; the lowest remaining fuel in any run
  is 72%).
- **Relay control: gradient ascent on λ₂** (the Fiedler value of the weighted
  communication Laplacian), following Zavlanos and Pappas, with a fallback that bridges
  components when the network has split. This extends earlier 2D work on adaptive
  communication topology to 3D.
- **Dynamics: point mass with per-role speed and acceleration limits.** Full 6-DOF
  dynamics would add cost without affecting the questions studied.
- **Occlusion: segment-versus-box line-of-sight tests against buildings.** Attackers fly
  low among the buildings and sentinels look down from altitude, so 3D geometry
  materially affects both detection and communication.
- **Guidance: 3D vector proportional navigation**, `a = N (Ω × v)` with
  `Ω = (r × v_rel) / |r|²`, applied to predicted track positions.
- **Visualization:** runs are recorded to JSON and played back in a Three.js viewer;
  metrics are plotted with Matplotlib. The simulation stays in Python for experiment
  throughput.

## Scenario

Attackers (configurable count, clustered approach directions, weaving and reactive
evasion) target a protected site at the origin. The default defense is 4 sentinels
(high-altitude cone sensors), 8 interceptors (fast, short-range seekers),
and 4 relays. An attacker leaks if it reaches the site and is intercepted if an
interceptor comes within the kill radius.

## Evaluation

- **Conditions** (16 defenders each): full (4 sentinels, 8 interceptors, 4 relays),
  no-relay (4 sentinels, 12 interceptors), and homogeneous (16 generalists).
- **E1, scaling:** 4, 8, 12, and 16 attackers, 10 seeds each. Metrics: interception
  rate; mean time to intercept (time from episode start to the kill, averaged over
  killed attackers only); mean time from an attacker's first detection by any
  defender sensor to its kill; network uptime (fraction of time fully connected);
  mean largest-component fraction; mean λ₂; and track coverage.
- **E2, node loss:** 8 attackers; 3 random defenders are destroyed at t = 15 s.
  Metrics: post-loss connectivity and interception rate.
- **Verification checks** run before experiments: single-interceptor convergence on
  straight and evasive targets; speed and acceleration limits recomputed from recorded
  positions; 4 relays versus 4 extra interceptors at a fixed team size of 16 (paired
  seeds); and the occlusion effect on low-flying attackers (paired seeds).

## Module map

| File | Contents |
|---|---|
| `sim/config.py` | Role profiles and constants |
| `sim/world.py` | Buildings and line-of-sight |
| `sim/comms.py` | Communication graph, λ₂, components, lossy track sharing |
| `sim/guidance.py` | Proportional navigation, waypoint flight, relay gradient, collision avoidance |
| `sim/allocation.py` | Auctions |
| `sim/engine.py` | Entities, simulation loop, attacker evasion, metrics |
| `tests/` | Unit tests |
| `run_sanity.py` | Verification checks |
| `run_experiments.py` | Experiments E1 and E2 |
| `export_run.py` | Demo recording for `viewer/` |
| `paper/paper.tex` | Paper |
