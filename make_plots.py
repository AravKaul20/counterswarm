"""Aggregate results/results.json into figures + a printed summary table."""
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = Path(__file__).resolve().parent / "results"
R = json.load(open(RESULTS / "results.json"))
CONDS = ("full", "norelay", "homog")
LABELS = {"full": "Heterogeneous, with relays", "norelay": "No relays (same team size)",
          "homog": "Homogeneous (same team size)"}
COLORS = {"full": "#2a78d6", "norelay": "#eb6834", "homog": "#1baf7a"}
MARKERS = {"full": "o", "norelay": "s", "homog": "^"}
NS = (4, 8, 12, 16)
N_SEEDS = len({m["seed"] for m in R["E1"] if m["team"] == "full" and m["n_threats"] == 4})

INK, INK2, RULE = "#1c2733", "#4f5d6d", "#d5dce4"
plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"], "font.size": 10.5,
    "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": RULE,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.major.size": 0, "ytick.major.size": 0,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e8ecf0", "grid.linewidth": 1,
    "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "axes.titlepad": 10, "legend.frameon": False, "savefig.facecolor": "white",
})


def agg(cond, n, key):
    vals = [m[key] for m in R["E1"] if m["team"] == cond and m["n_threats"] == n
            and m[key] is not None]
    return np.mean(vals), np.std(vals)


def figure_legend(fig, y):
    handles = [plt.Line2D([], [], color=COLORS[c], marker=MARKERS[c], lw=2, ms=7,
                          mec="white", mew=1.2, label=LABELS[c]) for c in CONDS]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.012, y), ncol=3,
               fontsize=10, handlelength=2.2, columnspacing=2.2)


# E1: four metrics as small multiples, x-dodged so error bars do not overlap
fig, axes = plt.subplots(2, 2, figsize=(10, 6.6))
panels = (("interception_rate", "Interception rate"),
          ("tti_mean", "Mean time from start to intercept (s)"),
          ("uptime", "Network uptime (fraction of time fully connected)"),
          ("l2_mean", "Mean algebraic connectivity, \u03bb\u2082"))
for ax, (key, title) in zip(axes.flat, panels):
    for k, c in enumerate(CONDS):
        mu = np.array([agg(c, n, key)[0] for n in NS])
        sd = np.array([agg(c, n, key)[1] for n in NS])
        x = np.array(NS) + (k - 1) * 0.28
        ax.errorbar(x, mu, yerr=sd, fmt="none", ecolor=COLORS[c], elinewidth=1.3, alpha=0.45)
        ax.plot(x, mu, color=COLORS[c], lw=2, marker=MARKERS[c], ms=7, mec="white", mew=1.2)
    ax.set_title(title)
    ax.set_xticks(NS)
    ax.set_xlim(2.8, 17.2)
for ax in axes[1]:
    ax.set_xlabel("Number of attackers")
axes[0, 0].set_ylim(0.5, 1.05)
fig.text(0.012, 0.99, "E1: performance as the attack grows", ha="left", va="top",
         fontsize=13, fontweight="semibold")
fig.text(0.012, 0.952, f"Mean \u00b1 1 SD over {N_SEEDS} seeds. Points are offset slightly so "
         "error bars do not overlap.", ha="left", va="top", fontsize=10, color=INK2)
figure_legend(fig, 0.925)
fig.tight_layout(rect=(0, 0, 1, 0.87), h_pad=2.2, w_pad=2.5)
fig.savefig(RESULTS / "e1_scaling.png", dpi=200)

# E2: connectivity over time around the node-loss event (mean line, interquartile band)
fig2, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.9))
grid = np.arange(0, 32, 0.25)
for c in CONDS:
    runs = [m for m in R["E2"] if m["team"] == c]
    for ax, key in ((a1, "l2"), (a2, "lcf")):
        Y = []
        for m in runs:
            ts, ys = np.array(m["series"]["t"]), np.array(m["series"][key])
            Y.append(np.interp(grid, ts, ys, right=np.nan))
        Y = np.array(Y)
        # only plot where at least 3 runs are still going (the tail is 1-2 run noise)
        valid = (~np.isnan(Y)).sum(axis=0) >= 3
        with np.errstate(all="ignore"):
            mu = np.where(valid, np.nanmean(Y, axis=0), np.nan)
            q1 = np.where(valid, np.nanpercentile(Y, 25, axis=0), np.nan)
            q3 = np.where(valid, np.nanpercentile(Y, 75, axis=0), np.nan)
        ax.fill_between(grid, q1, q3, color=COLORS[c], alpha=0.14, lw=0)
        ax.plot(grid, mu, color=COLORS[c], lw=2)
for ax, title in ((a1, "Algebraic connectivity, \u03bb\u2082"),
                  (a2, "Largest connected fraction of the team")):
    ax.axvline(15, color=INK2, lw=1.2, ls=(0, (4, 3)))
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_xlim(0, 32)
a1.set_ylim(0, None)
a2.set_ylim(0.6, 1.02)
a1.annotate("3 defenders lost", xy=(15, 1), xycoords=("data", "axes fraction"),
            xytext=(5, -4), textcoords="offset points", va="top", fontsize=9.5, color=INK2)
a2.annotate("3 defenders lost", xy=(15, 0), xycoords=("data", "axes fraction"),
            xytext=(5, 6), textcoords="offset points", va="bottom", fontsize=9.5, color=INK2)
fig2.text(0.012, 0.985, "E2: recovery after losing 3 of 16 defenders at 15 s", ha="left",
          va="top", fontsize=13, fontweight="semibold")
fig2.text(0.012, 0.915, f"Line: mean over {N_SEEDS} seeds. Band: interquartile range.",
          ha="left", va="top", fontsize=10, color=INK2)
handles = [plt.Line2D([], [], color=COLORS[c], lw=2.4, label=LABELS[c]) for c in CONDS]
fig2.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.012, 0.865), ncol=3,
            fontsize=10, handlelength=2.2, columnspacing=2.2)
fig2.tight_layout(rect=(0, 0, 1, 0.77), w_pad=2.5)
fig2.savefig(RESULTS / "e2_resilience.png", dpi=200)

# printed summary (audited numbers for the paper and README)
def betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b), by Lentz's continued fraction."""
    if x <= 0.0 or x >= 1.0:
        return float(x >= 1.0)
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - betainc(b, a, 1.0 - x)
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log(1.0 - x)) / a
    tiny, f, c, d = 1e-300, 1.0, 1.0, 0.0
    for i in range(400):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + num / c
        c = c if abs(c) > tiny else tiny
        f *= c * d
        if abs(1.0 - c * d) < 1e-14:
            break
    return front * (f - 1.0)


def welch(a, b):
    """Welch's unequal-variance t-test: (t, df, two-sided p)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    t = (a.mean() - b.mean()) / math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    return t, df, betainc(df / 2.0, 0.5, df / (df + t * t))


def vals(cond, n, key):
    return [m[key] for m in R["E1"] if m["team"] == cond and m["n_threats"] == n
            and m[key] is not None]


print(f"=== E1 summary (mean over {N_SEEDS} seeds) ===")
print("tti = start-to-kill time over killed threats; det = first-detection time over detected")
print("threats; d2k = first-detection-to-kill time over killed threats (all in seconds)")
keys = ("interception_rate", "tti_mean", "detect_mean", "detect_to_kill_mean", "uptime",
        "l2_mean", "lcf_mean", "tracked_mean")
print(f"{'cond':10s} {'n':>3s} {'rate':>6s} {'tti':>6s} {'det':>6s} {'d2k':>6s} {'uptime':>7s} "
      f"{'l2':>6s} {'lcf':>6s} {'tracked':>8s}")
for c in CONDS:
    for n in NS:
        row = [agg(c, n, k)[0] for k in keys]
        print(f"{c:10s} {n:3d} {row[0]:6.2f} {row[1]:6.1f} {row[2]:6.1f} {row[3]:6.1f} "
              f"{row[4]:7.2f} {row[5]:6.2f} {row[6]:6.2f} {row[7]:8.2f}")

print("\nE1 lambda2 ratios (unrounded means; lambda2 edge weights scale with radio range,")
print("so ratios across teams with different radios are not like-for-like):")
for n in NS:
    l2 = {c: agg(c, n, "l2_mean")[0] for c in CONDS}
    print(f"  n={n:2d} full/norelay={l2['full'] / l2['norelay']:.2f} "
          f"full/homog={l2['full'] / l2['homog']:.2f} homog/norelay={l2['homog'] / l2['norelay']:.2f}")

print("\nE1 Welch t-tests (10 vs 10 seeds; t > 0 means the first team's mean is larger):")
for key, a, b in (("tti_mean", "full", "homog"), ("tti_mean", "norelay", "homog"),
                  ("detect_mean", "full", "homog"), ("detect_to_kill_mean", "full", "homog"),
                  ("tracked_mean", "full", "homog"), ("interception_rate", "norelay", "full"),
                  ("uptime", "full", "norelay"), ("uptime", "full", "homog")):
    for n in NS:
        x, y = vals(a, n, key), vals(b, n, key)
        t, df, p = welch(x, y)
        print(f"  {key:20s} {a:>7s} vs {b:5s} n={n:2d}: diff={np.mean(x) - np.mean(y):+7.3f} "
              f"t={t:+5.2f} df={df:4.1f} p={p:.3f}")

print("\nFuel and floor (E1 and E2, all runs):")
for c in CONDS:
    runs = [m for m in R["E1"] + R["E2"] if m["team"] == c]
    fm = [m["fuel_min"] for m in runs if m["fuel_min"] is not None]
    e1 = [m for m in R["E1"] if m["team"] == c]
    print(f"  {c:8s} episode length {min(m['t_end'] for m in runs):.1f}-{max(m['t_end'] for m in runs):.1f} s; "
          f"min remaining fuel fraction {min(fm) if fm else float('nan'):.3f}; "
          f"E1 defender losses {sum(m['defender_losses'] for m in e1)}; "
          f"floor contacts per run {np.mean([m['floor_contacts'] for m in runs]):.1f}")

print(f"\n=== E2 summary (3 of 16 defenders lost at 15 s; post-loss window; mean over {N_SEEDS} seeds) ===")
l2_post = {}
for c in CONDS:
    runs = [m for m in R["E2"] if m["team"] == c]
    def pm(k):
        v = [m[k] for m in runs if m[k] is not None]
        return np.mean(v), np.std(v)
    l2_post[c] = []
    for m in runs:
        ts, ys = np.array(m["series"]["t"]), np.array(m["series"]["l2"])
        l2_post[c].append(ys[ts >= 15].mean())
    print(f"{c:10s} rate={pm('interception_rate')[0]:.2f} "
          f"uptime_post={pm('uptime_post')[0]:.2f}+-{pm('uptime_post')[1]:.2f} "
          f"lcf_post={pm('lcf_post')[0]:.2f}+-{pm('lcf_post')[1]:.2f} "
          f"l2_post={np.mean(l2_post[c]):.2f}+-{np.std(l2_post[c]):.2f}")
mu = {c: np.mean(v) for c, v in l2_post.items()}
print(f"E2 l2_post ratios (unrounded): full/norelay={mu['full'] / mu['norelay']:.2f} "
      f"homog/norelay={mu['homog'] / mu['norelay']:.2f} full/homog={mu['full'] / mu['homog']:.2f}")
print("E2 Welch t-tests (post-loss window unless noted):")
e2 = {c: [m for m in R["E2"] if m["team"] == c] for c in CONDS}
for key, a, b in (("uptime_post", "full", "norelay"), ("uptime_post", "full", "homog"),
                  ("lcf_post", "full", "homog"), ("interception_rate", "norelay", "full")):
    x, y = [m[key] for m in e2[a]], [m[key] for m in e2[b]]
    t, df, p = welch(x, y)
    print(f"  {key:20s} {a:>7s} vs {b:7s}: diff={np.mean(x) - np.mean(y):+7.3f} "
          f"t={t:+5.2f} df={df:4.1f} p={p:.3f}")
for a, b in (("full", "norelay"), ("full", "homog")):
    t, df, p = welch(l2_post[a], l2_post[b])
    print(f"  {'l2_post':20s} {a:>7s} vs {b:7s}: diff={np.mean(l2_post[a]) - np.mean(l2_post[b]):+7.3f} "
          f"t={t:+5.2f} df={df:4.1f} p={p:.3f}")
first = np.array([m["t_first_kill"] for m in R["E2"] if m["t_first_kill"] is not None])
print(f"E2 first intercept time over all runs: earliest={first.min():.2f} s "
      f"median={np.median(first):.2f} s; runs with a kill before 15 s: "
      f"{int(np.sum(first < 15.0))}/{len(R['E2'])}; fraction of team lost = 3/16 = {3 / 16:.3f}")
print("\nwrote results/e1_scaling.png, results/e2_resilience.png")
