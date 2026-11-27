"""Figures for the manuscript (300 dpi PNG, serif font metric-compatible with Times New Roman)."""
import os
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import arviz  # noqa: F401  (keeps environment consistent with the analysis)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(FIG, exist_ok=True)
BLUE, ORANGE, INK, MUTED, GRID = "#257de0", "#f47230", "#191919", "#666666", "#e6e6e6"
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 10, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.axisbelow": True, "savefig.dpi": 300})
DR = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
LABEL = {"DVOP": "DevOps maturity", "AIAD": "AI-agent assistance", "MSVC": "Microservice complexity",
         "CLAU": "Cloud automation", "MTEX": "Team experience", "SECU": "Security practices"}

q = pd.read_csv(os.path.join(OUT, "quarter.csv"))
r = pd.read_csv(os.path.join(OUT, "repo.csv"))

# Figure 1: size and effort at two levels
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.3))
hb = ax[0].hexbin(q["ln_ksloc"], q["ln_pm"], gridsize=35, cmap="Blues", mincnt=1, linewidths=0.2)
xs = np.linspace(q["ln_ksloc"].min(), q["ln_ksloc"].max(), 50)
b = np.polyfit(q["ln_ksloc"], q["ln_pm"], 1)
ax[0].plot(xs, np.polyval(b, xs), color=ORANGE, lw=2, label=f"Pooled fit, B = {b[0]:.2f}")
ax[0].set_xlabel("ln size per quarter (KSLOC)"); ax[0].set_ylabel("ln effort per quarter (PM)")
ax[0].set_title("(a) Repository-quarters (n = 5,932)", fontsize=10, color=INK, loc="left")
ax[0].legend(frameon=False, fontsize=8, loc="upper left")
cb = fig.colorbar(hb, ax=ax[0], pad=0.01); cb.set_label("Quarters", fontsize=8); cb.ax.tick_params(labelsize=7)
sc = ax[1].scatter(r["ln_ksloc"], r["ln_pm"], c=r["n_quarters"], cmap="Blues", vmin=0, vmax=22, s=12,
                   edgecolors="white", linewidths=0.4)
b2 = np.polyfit(r["ln_ksloc"], r["ln_pm"], 1)
xs = np.linspace(r["ln_ksloc"].min(), r["ln_ksloc"].max(), 50)
ax[1].plot(xs, np.polyval(b2, xs), color=ORANGE, lw=2, label=f"Pooled fit, B = {b2[0]:.2f}")
ax[1].set_xlabel("ln total size (KSLOC)"); ax[1].set_ylabel("ln total effort (PM)")
ax[1].set_title("(b) Repository totals (n = 386)", fontsize=10, color=INK, loc="left")
ax[1].legend(frameon=False, fontsize=8, loc="upper left")
cb = fig.colorbar(sc, ax=ax[1], pad=0.01); cb.set_label("Quarters observed", fontsize=8); cb.ax.tick_params(labelsize=7)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure1_size_effort.png")); plt.close(fig)

# Figure 2: driver effects (full-range effort ratio) at both levels
lv = {"Repository level": ("rq1_repo_literature_duration_draws.npz", BLUE, "o"),
      "Repository-quarter level": ("rq1_quarter_literature_draws.npz", ORANGE, "s")}
fig, ax = plt.subplots(figsize=(6.2, 3.6))
ypos = np.arange(len(DR))[::-1]
for k, (name, (f, col, mk)) in enumerate(lv.items()):
    D = np.load(os.path.join(OUT, f), allow_pickle=True)
    for i, d in enumerate(DR):
        x = np.exp(D[d]); m, lo, hi = np.median(x), np.quantile(x, 0.025), np.quantile(x, 0.975)
        y = ypos[i] + (0.17 if k == 0 else -0.17)
        ax.plot([lo, hi], [y, y], color=col, lw=2, solid_capstyle="round")
        ax.plot(m, y, mk, color=col, ms=6, mec="white", mew=0.8, label=name if i == 0 else None)
ax.axvline(1, color=MUTED, lw=1, ls="--")
ax.set_xscale("log"); ax.set_xticks([0.25, 0.5, 1, 2]); ax.set_xticklabels(["0.25", "0.5", "1", "2"])
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_yticks(ypos); ax.set_yticklabels([LABEL[d] for d in DR]); ax.grid(axis="y", visible=False)
ax.set_xlabel("Effort ratio, highest vs lowest driver score (median and 95% credible interval)")
ax.legend(frameon=False, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure2_driver_effects.png")); plt.close(fig)

# Figure 3: event study for effort and productivity
ev = pd.read_csv(os.path.join(OUT, "rq2_event_study.csv"))
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
for a, (y, title) in zip(ax, [("ln_pm", "(a) Effort"), ("ln_prod", "(b) Productivity (KSLOC per PM)")]):
    e = ev[ev["outcome"] == y].sort_values("e")
    pct = lambda v: 100 * (np.exp(v) - 1)
    a.axhline(0, color=MUTED, lw=1); a.axvline(-0.5, color=MUTED, lw=1, ls="--")
    a.fill_between(e["e"], pct(e["ci_low"]), pct(e["ci_high"]), color=BLUE, alpha=0.18, lw=0)
    a.plot(e["e"], pct(e["att"]), "-o", color=BLUE, lw=2, ms=5, mec="white", mew=0.8)
    a.set_title(title, fontsize=10, color=INK, loc="left"); a.set_xlabel("Quarters relative to AI adoption")
    a.set_xticks(range(-6, 5))
ax[0].set_ylabel("Change vs last quarter before adoption (%)")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure3_event_study.png")); plt.close(fig)

# Figure 4: simulated effort ratio when each driver moves from a low to a high observed value
s = pd.read_csv(os.path.join(OUT, "rq4_scenarios.csv"))
fig, ax = plt.subplots(figsize=(6.2, 3.2))
ypos = np.arange(len(s))[::-1]
for i, row in s.iterrows():
    ax.plot([row["ci90_low"], row["ci90_high"]], [ypos[i]] * 2, color=BLUE, lw=2, solid_capstyle="round")
    ax.plot(row["effort_ratio_median"], ypos[i], "o", color=BLUE, ms=6, mec="white", mew=0.8)
    ax.text(row["ci90_high"] + 0.01, ypos[i], f"{row['from']:.2f} to {row['to']:.2f}", va="center",
            fontsize=8, color=MUTED)
ax.axvline(1, color=MUTED, lw=1, ls="--")
ax.set_yticks(ypos); ax.set_yticklabels([LABEL[d] for d in s["driver"]]); ax.grid(axis="y", visible=False)
ax.set_xlabel("Simulated effort ratio (median and 90% interval); labels show the score change")
ax.set_xlim(0.6, 1.3)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure4_scenarios.png")); plt.close(fig)
print("figures written to", FIG)
