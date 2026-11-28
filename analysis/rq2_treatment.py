"""RQ2 under alternative definitions of AI adoption.

The main analysis dates adoption by the first quarter with any AI signal: a merged agent-written pull
request (AIDev), an AI-written or AI-co-written commit, or an AI assistant configuration file. These
signals differ in what they show. This script (1) counts adopters by group and by first signal and
(2) reruns the difference-in-differences under stricter definitions. Repositories with an AI signal
that the definition does not use are dropped, so they serve neither as treated nor as controls.
Outputs: out/rq2_treatment_counts.csv, out/rq2_treatment.csv (Supplementary Table S16).
"""
import os
import numpy as np
import pandas as pd
import rq2_did as R

a = pd.read_csv(os.path.join(R.OUT, "all_quarters.csv"))
ws = pd.to_datetime(a["window_start"], utc=True)
a["tq"] = ws.dt.year * 4 + (ws.dt.month - 1) // 3 + 1 - (2021 * 4 + 1)
first = lambda m: a[m].groupby("repo")["tq"].min()
f_pr = first(a["agent_merged_prs"].fillna(0) > 0)
f_cm = first(a["ai_commit_share"].fillna(0) > 0)
f_cf = first(a["has_ai_config"] == 1)
S = pd.DataFrame({"pr": f_pr, "commit": f_cm, "config": f_cf}).reindex(a["repo"].unique())
S["any"] = S[["pr", "commit", "config"]].min(axis=1)

base = pd.read_csv(os.path.join(R.OUT, "quarter.csv"))
base["t"] = base["quarter"].str[:4].astype(int) * 4 + base["quarter"].str[-1].astype(int) - (2021 * 4 + 1)
base["ln_prod"] = np.log(base["ksloc"] / base["effort_pm"])
base["ln_team"] = np.log(base["team_size"])
grp = base.groupby("repo")["group"].first()

# ---- counts in the main analysis sample (as rq2_did: adopters in the first quarter are dropped)
reps = base["repo"].unique()
Sm = S.reindex(reps)
inmain = Sm["any"].isna() | (Sm["any"] > 0)
Sm, gm = Sm[inmain], grp.reindex(Sm.index[inmain])
adopt = Sm["any"].notna()
def first_signal(r):
    order = [k for k in ["pr", "commit", "config"] if r[k] == r["any"]]
    return "+".join(order)
fs = Sm[adopt].apply(first_signal, axis=1)
counts = pd.DataFrame({
    "AI group (AIDev)": [int((adopt & (gm == "ai")).sum()), int((~adopt & (gm == "ai")).sum())],
    "Comparison group": [int((adopt & (gm == "control")).sum()), int((~adopt & (gm == "control")).sum())],
}, index=["Adopters (any signal)", "Never adopted"])
counts.to_csv(os.path.join(R.OUT, "rq2_treatment_counts.csv"))
print(counts)
print("first signal among adopters:\n", pd.crosstab(fs, gm[adopt]))
print("agent adopters with an earlier commit/config signal:",
      int(((Sm["pr"].notna()) & (Sm["any"] < Sm["pr"])).sum()))

# ---- alternative treatment definitions
def defin(name, g, drop):
    """g: adoption quarter per repo (NaN = control); drop: repos excluded altogether."""
    d = base[~base["repo"].isin(drop)].copy()
    d["g"] = d["repo"].map(g)
    d = d[~(d["g"] <= 0)]
    return name, d

has_any = S["any"].notna()
defs = [
    defin("Main: first quarter with any signal", S["any"], []),
    defin("Agent adopters (AIDev), dated by first agent pull request", S["pr"], S.index[has_any & S["pr"].isna()]),
    defin("Agent adopters with no earlier commit or configuration signal",
          S["pr"].where(S["pr"] <= S["any"]), S.index[has_any & ~(S["pr"].notna() & (S["pr"] <= S["any"]))]),
    defin("Commit or configuration signals only (no agent pull requests)",
          S["any"].where(S["pr"].isna()), S.index[S["pr"].notna()]),
    defin("Agent pull request or AI commit (configuration files ignored)", S[["pr", "commit"]].min(axis=1),
          S.index[has_any & S["pr"].isna() & S["commit"].isna()]),
]
rows = []
for name, d in defs:
    for y in ["ln_pm", "ln_team", "ln_ksloc", "ln_prod"]:
        r, _ = R.run(d, y, name)
        rows.append(r)
        p = lambda v: 100 * (np.exp(v) - 1)
        print(f"{name[:58]:58s} {y:8s} {p(r['att']):+6.1f}% [{p(r['ci_low']):+6.1f}, {p(r['ci_high']):+6.1f}] "
              f"pre {p(r['pre_avg']):+5.1f}%  n={r['n_treated_repos']}/{r['n_never']}", flush=True)
pd.DataFrame(rows).to_csv(os.path.join(R.OUT, "rq2_treatment.csv"), index=False)
