"""Aggregate results/results.json into figures + a printed summary table."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = json.load(open("results/results.json"))
CONDS = ("full", "norelay", "homog")
LABELS = {"full": "heterogeneous (relays)", "norelay": "no-relay (equal budget)",
          "homog": "homogeneous (equal budget)"}
COLORS = {"full": "#2274a5", "norelay": "#e26d5c", "homog": "#7d8570"}
NS = (4, 8, 12, 16)
N_SEEDS = len({m["seed"] for m in R["E1"] if m["team"] == "full" and m["n_threats"] == 4})


def agg(cond, n, key):
    vals = [m[key] for m in R["E1"] if m["team"] == cond and m["n_threats"] == n
            and m[key] is not None]
    return np.mean(vals), np.std(vals)


fig, axes = plt.subplots(2, 2, figsize=(11, 8))
for key, ax, ylab in ((("interception_rate"), axes[0, 0], "interception rate"),
                      (("tti_mean"), axes[0, 1], "mean time-to-intercept [s]"),
                      (("uptime"), axes[1, 0], "mesh uptime (fully connected fraction)"),
                      (("l2_mean"), axes[1, 1], "mean algebraic connectivity $\\lambda_2$")):
    for c in CONDS:
        mu = [agg(c, n, key)[0] for n in NS]
        sd = [agg(c, n, key)[1] for n in NS]
        ax.errorbar(NS, mu, yerr=sd, marker="o", capsize=3, label=LABELS[c],
                    color=COLORS[c])
    ax.set_xlabel("threat swarm size")
    ax.set_ylabel(ylab)
    ax.set_xticks(NS)
    ax.grid(alpha=.3)
axes[0, 0].legend(fontsize=8)
axes[0, 0].set_ylim(0, 1.05)
fig.suptitle(f"E1: scaling with threat swarm size ({N_SEEDS} seeds, mean $\\pm$ sd)")
fig.tight_layout()
fig.savefig("results/e1_scaling.png", dpi=160)

# E2: connectivity time series around the node-loss event
fig2, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
grid = np.arange(0, 32, 0.25)
for c in CONDS:
    runs = [m for m in R["E2"] if m["team"] == c]
    for ax, key in ((a1, "l2"), (a2, "lcf")):
        Y = []
        for m in runs:
            ts, ys = np.array(m["series"]["t"]), np.array(m["series"][key])
            Y.append(np.interp(grid, ts, ys, right=np.nan))
        Y = np.array(Y)
        # only plot where at least 3 runs are still alive (tail is 1-2 run noise)
        valid = (~np.isnan(Y)).sum(axis=0) >= 3
        with np.errstate(all="ignore"):
            mu = np.where(valid, np.nanmean(Y, axis=0), np.nan)
            sd = np.where(valid, np.nanstd(Y, axis=0), np.nan)
        ax.plot(grid, mu, color=COLORS[c], label=LABELS[c])
        ax.fill_between(grid, mu - sd, mu + sd, color=COLORS[c], alpha=.15)
for ax, ylab in ((a1, "$\\lambda_2$"), (a2, "largest-component fraction")):
    ax.axvline(15, color="k", ls="--", lw=1, label="3 defenders killed")
    ax.set_xlabel("time [s]")
    ax.set_ylabel(ylab)
    ax.grid(alpha=.3)
a1.legend(fontsize=8)
fig2.suptitle(f"E2: mesh resilience to loss of 3 random defenders at t=15 s ({N_SEEDS} seeds)")
fig2.tight_layout()
fig2.savefig("results/e2_resilience.png", dpi=160)

# printed summary (audited numbers for the paper)
print(f"=== E1 summary (mean over {N_SEEDS} seeds) ===")
print(f"{'cond':10s} {'n':>3s} {'rate':>6s} {'tti':>6s} {'uptime':>7s} {'l2':>6s} {'lcf':>6s} {'tracked':>8s}")
for c in CONDS:
    for n in NS:
        row = [agg(c, n, k)[0] for k in
               ("interception_rate", "tti_mean", "uptime", "l2_mean", "lcf_mean", "tracked_mean")]
        print(f"{c:10s} {n:3d} {row[0]:6.2f} {row[1]:6.1f} {row[2]:7.2f} {row[3]:6.2f} {row[4]:6.2f} {row[5]:8.2f}")

print(f"\n=== E2 summary (post-kill window, mean over {N_SEEDS} seeds) ===")
for c in CONDS:
    runs = [m for m in R["E2"] if m["team"] == c]
    def pm(k):
        v = [m[k] for m in runs if m[k] is not None]
        return np.mean(v), np.std(v)
    l2_post = []
    for m in runs:
        ts, ys = np.array(m["series"]["t"]), np.array(m["series"]["l2"])
        l2_post.append(ys[ts >= 15].mean())
    print(f"{c:10s} rate={pm('interception_rate')[0]:.2f} "
          f"uptime_post={pm('uptime_post')[0]:.2f}+-{pm('uptime_post')[1]:.2f} "
          f"lcf_post={pm('lcf_post')[0]:.2f}+-{pm('lcf_post')[1]:.2f} "
          f"l2_post={np.mean(l2_post):.2f}+-{np.std(l2_post):.2f}")
print("\nwrote results/e1_scaling.png, results/e2_resilience.png")
