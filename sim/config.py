"""Global constants and role capability profiles."""
import numpy as np

DT = 0.05                 # integration step [s]
SIM_TIME = 120.0          # max episode length [s]
ALLOC_PERIOD = 20         # ticks between auction rounds (1 s)
CONN_PERIOD = 5           # ticks between connectivity evaluations (0.25 s)

TRACK_FRESH = 2.0         # track age considered fresh enough to bid on [s]
TRACK_STALE = 5.0         # coasted tracks older than this are dropped [s]
SENSE_NOISE_P = 2.0       # position measurement noise sigma [m]
SENSE_NOISE_V = 1.0       # velocity measurement noise sigma [m/s]

KILL_RADIUS = 6.0         # interceptor-threat miss distance for a kill [m]
ASSET_POS = np.array([0.0, 0.0, 15.0])
ASSET_RADIUS = 30.0       # threat reaching this sphere = leak

PN_GAIN = 4.0

# Communication link model: link exists if d < min(comm_i, comm_j) and LOS clear.
# Laplacian edge weight w = exp(-(d/(SIGMA_FRAC*R))^2); per-track delivery
# probability p = max(P_FLOOR, 1 - (d/R)^4).
SIGMA_FRAC = 0.6
P_FLOOR = 0.15

ROLES = {
    # vmax [m/s], amax [m/s^2], cruise speed, comm range [m], sensor model
    "sentinel": dict(vmax=12.0, amax=4.0, cruise=8.0, comm=420.0,
                     sensor="cone", s_range=450.0, s_half=np.deg2rad(70.0)),
    "interceptor": dict(vmax=42.0, amax=28.0, cruise=12.0, comm=300.0,
                        sensor="sphere", s_range=160.0, fuel=100.0),
    "relay": dict(vmax=18.0, amax=8.0, cruise=10.0, comm=420.0, sensor=None),
    # equal-budget homogeneous baseline agent
    "generalist": dict(vmax=26.0, amax=13.0, cruise=12.0, comm=300.0,
                       sensor="sphere", s_range=300.0, fuel=160.0),
}

THREAT = dict(vmax=25.0, amax=15.0, cruise_alt=(15.0, 35.0),
              weave_a=6.0, jink_a=13.0, jink_range=130.0)

SENTINEL_STATION_R = 260.0   # radius of sentinel station ring [m]
SENTINEL_STATION_ALT = 150.0
RELAY_ALT_BAND = (60.0, 110.0)
