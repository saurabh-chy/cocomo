"""RQ2: effect of AI adoption, staggered difference-in-differences (Callaway & Sant'Anna, 2021).
Unconditional estimator with long differences from the last pre-adoption quarter (g-1); controls are
never-adopters and not-yet-adopters. Confidence intervals from a repository-clustered bootstrap."""
import os
import numpy as np, pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
E_MIN, E_MAX, N_BOOT, SEED = -6, 4, 499, 20261127

q = pd.read_csv(os.path.join(OUT, "quarter.csv"))
q["t"] = q["quarter"].str[:4].astype(int) * 4 + q["quarter"].str[-1].astype(int) - (2021 * 4 + 1)
adopt = pd.to_datetime(q.groupby("repo")["ai_adopt_start"].first(), utc=True)
g = (adopt.dt.year * 4 + (adopt.dt.month - 1) // 3 + 1 - (2021 * 4 + 1))
q["g"] = q["repo"].map(g)                      # NaN = never adopts
q = q[~(q["g"] <= 0)]                          # adopted in the first quarter: no pre-period
q["ln_prod"] = np.log(q["ksloc"] / q["effort_pm"])     # KSLOC per person-month
OUTCOMES = {"ln_pm": "ln effort (PM)", "ln_prod": "ln productivity (KSLOC/PM)", "ln_ksloc": "ln size (KSLOC)"}
T = int(q["t"].max())

def prepare_cells(df, y):
    """All (cohort, quarter) cells with the repository indices and long differences they use."""
    w = df.pivot_table(index="repo", columns="t", values=y)
    gg = df.groupby("repo")["g"].first().reindex(w.index).values
    W = w.values
    cols = {t: i for i, t in enumerate(w.columns)}
    cells = []
    for gv in sorted(set(gg[~np.isnan(gg)])):
        gv = int(gv); base = gv - 1
        if base not in cols:
            continue
        tr_mask = gg == gv
        for t in range(max(0, gv + E_MIN), min(T, gv + E_MAX) + 1):
            if t not in cols or t == base:
                continue
            ctrl_mask = (np.isnan(gg) | (gg > max(t, base))) & ~tr_mask
            d = W[:, cols[t]] - W[:, cols[base]]
            it = np.where(tr_mask & ~np.isnan(d))[0]; ic = np.where(ctrl_mask & ~np.isnan(d))[0]
            if len(it) >= 3 and len(ic) >= 10:
                cells.append((gv, t, t - gv, it, ic, d))
    return cells, len(w)

def estimate(cells, wts):
    rows = []
    for gv, t, e, it, ic, d in cells:
        wt, wc = wts[it], wts[ic]
        if wt.sum() == 0 or wc.sum() == 0:
            continue
        rows.append((e, np.average(d[it], weights=wt) - np.average(d[ic], weights=wc), wt.sum()))
    r = pd.DataFrame(rows, columns=["e", "att", "n"])
    ev = r.groupby("e").apply(lambda c: np.average(c["att"], weights=c["n"]), include_groups=False)
    post, pre = r[r["e"] >= 0], r[r["e"] < -1]
    return (ev, np.average(post["att"], weights=post["n"]) if len(post) else np.nan,
            np.average(pre["att"], weights=pre["n"]) if len(pre) else np.nan)

def run(df, y, label):
    cells, nrep = prepare_cells(df, y)
    ev, overall, pre = estimate(cells, np.ones(nrep))
    rng = np.random.default_rng(SEED)
    bo, bp, be = [], [], []
    for _ in range(N_BOOT):               # repository-clustered bootstrap as multinomial reweighting
        wts = rng.multinomial(nrep, np.full(nrep, 1 / nrep)).astype(float)
        e2, o2, p2 = estimate(cells, wts)
        bo.append(o2); bp.append(p2); be.append(e2)
    be = pd.DataFrame(be)
    res = {"subset": label, "outcome": y, "att": overall, "ci_low": np.nanpercentile(bo, 2.5),
           "ci_high": np.nanpercentile(bo, 97.5), "pre_avg": pre, "pre_ci_low": np.nanpercentile(bp, 2.5),
           "pre_ci_high": np.nanpercentile(bp, 97.5),
           "n_treated_repos": int(df.loc[df["g"].notna(), "repo"].nunique()),
           "n_never": int(df.loc[df["g"].isna(), "repo"].nunique()), "n_cells": len(cells)}
    evdf = pd.DataFrame({"e": ev.index, "att": ev.values, "ci_low": be.quantile(0.025).reindex(ev.index).values,
                         "ci_high": be.quantile(0.975).reindex(ev.index).values})
    return res, evdf

if __name__ == "__main__":
    rows, events = [], []
    for y in OUTCOMES:
        r, ev = run(q, y, "all")
        rows.append(r)
        ev["outcome"] = y
        events.append(ev)
        print(f"{OUTCOMES[y]:30s} ATT={r['att']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]  "
              f"pre-trend avg={r['pre_avg']:+.3f}  treated={r['n_treated_repos']} never={r['n_never']}")
    for label, mask in [("company-led", q["company_led"] == 1), ("community", q["company_led"] == 0)]:
        sub = q[mask]
        r, _ = run(sub, "ln_pm", label)
        rows.append(r)
        print(f"{label:30s} ln_pm ATT={r['att']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]")
    # experienced vs less experienced teams (MTEX in the base quarter above / below the median)
    base_mtex = q[q["t"] == q["g"] - 1].set_index("repo")["MTEX"]
    med = q.groupby("repo")["MTEX"].mean().median()
    hi = set(base_mtex[base_mtex >= med].index)
    for label, keep in [("experienced teams", lambda r: r in hi), ("less experienced teams", lambda r: r not in hi)]:
        sub = q[q["g"].isna() | q["repo"].map(keep)]
        r, _ = run(sub, "ln_pm", label)
        rows.append(r)
        print(f"{label:30s} ln_pm ATT={r['att']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]")
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "rq2_att.csv"), index=False)
    pd.concat(events).to_csv(os.path.join(OUT, "rq2_event_study.csv"), index=False)
