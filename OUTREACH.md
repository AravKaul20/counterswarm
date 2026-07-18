# Plain-language summary (for outreach email)

I built a 3D simulation of a drone-versus-drone defense problem: a defending
team of sixteen drones protects a site against an incoming swarm of up to
sixteen evasive attackers flying low among buildings. The defenders are
deliberately *not* interchangeable — slow high-altitude "sentinels" carry the
wide-area sensors, fast short-endurance "interceptors" do the chasing using a
3D missile-guidance law, and "relays" exist only to keep the team's wireless
mesh connected, steering themselves along the gradient of the network's
algebraic connectivity (a graph-theoretic measure of how far the network is
from splitting).

The interesting part is the coupling. Nothing in the system is globally known:
sensors are blocked by buildings, radio links break with distance and
line-of-sight, and the auction that assigns pursuers to targets can only run
among drones that can actually talk to each other. So when an interceptor
sprints after a target, it physically tears at the same network that is
feeding it target updates — and the relays have to fly to repair the damage
while the engagement is still happening.

Two results came out of the experiments (10 random seeds per condition, with a
homogeneous same-size team and a relay-free same-size team as baselines). The
specialist team detects earlier and intercepts consistently faster than the
homogeneous team at every attack size tested (roughly 1–3 seconds faster on
average, with better track coverage throughout). And the relays multiply the
network's connectivity margin by 2.3–4.5× — the larger factor measured after a
quarter of the team is knocked out mid-engagement — but they do *not* raise
the raw interception rate: at the largest attack sizes, spending those four
slots on extra interceptors kills more drones, at the cost of a far more
fragile network. That trade-off between
"effector capacity" and "information-flow margin" only becomes visible when
allocation, sensing, and connectivity are simulated together, and it extends
my earlier 2D work on adaptive communication topology into full 3D with
occlusion and heterogeneous roles.

The project is ~850 lines of Python plus a ~200-line interactive Three.js
viewer for watching engagements in 3D; the paper draft, code, and experiment
data are included.
