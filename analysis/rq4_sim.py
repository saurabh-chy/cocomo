"""RQ4: simulation built entirely from the fitted repository-quarter model and the observed data.
Inputs: posterior draws (rq1_quarter_literature_draws.npz) and observed repository-quarters."""
import os
import numpy as np, pandas as pd
from scipy.stats import ks_2samp
from SALib.sample import sobol as sobol_sample
from SALib.analyze import sobol

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
DRIVERS = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
SEED, NSIM = 20261127, 20000
rng = np.random.default_rng(SEED)

q = pd.read_csv(os.path.join(OUT, "quarter.csv"))
D = np.load(os.path.join(OUT, "rq1_quarter_literature_draws.npz"), allow_pickle=True)
names = list(D["control_names"]); lk_mean = float(D["lk_mean"])
C = pd.get_dummies(q["language"], prefix="lang", drop_first=True, dtype=float)
C["company_led"] = q["company_led"].astype(float)
C["age_years"] = (q["age_years"] - q["age_years"].mean()) / q["age_years"].std()
C["bot_share"] = q["bot_share"]
C = C.join(pd.get_dummies(q["quarter"], prefix="q", drop_first=True, dtype=float))
C = C.reindex(columns=names, fill_value=0.0).values
ndraw = len(D["B"])

def linpred(rows, k, drivers=None, lnk=None):
    """Linear predictor for row indices `rows` under posterior draw k (no repository or residual noise)."""
    dv = q[DRIVERS].values[rows] if drivers is None else drivers
    lk = np.log(q["ksloc"].values[rows]) if lnk is None else lnk
    g = np.array([D[d][k] for d in DRIVERS]).T if np.ndim(k) else np.array([D[d][k] for d in DRIVERS])
    if np.ndim(k):
        return (D["lnA"][k] + D["B"][k] * (lk - lk_mean) + np.sum(g * dv, axis=1)
                + np.sum(C[rows] * D["controls"][k], axis=1))
    return D["lnA"][k] + D["B"][k] * (lk - lk_mean) + dv @ g + C[rows] @ D["controls"][k]

def simulate(rows):
    k = rng.integers(0, ndraw, size=len(rows))
    mu = linpred(rows, k)
    return mu + rng.normal(0, D["sigma_repo"][k]) + rng.normal(0, D["sigma"][k])

# 1 validation: simulate the 2025-2026 quarters from their own profiles and compare with what happened
hold = np.where(q["quarter"].str[:4].astype(int) >= 2025)[0]
sim_h = simulate(np.repeat(hold, 10))
ks = ks_2samp(sim_h, q["ln_pm"].values[hold])
qs = [0.05, 0.25, 0.5, 0.75, 0.95]
val = pd.DataFrame({"quantile": qs, "observed_pm": np.exp(np.quantile(q["ln_pm"].values[hold], qs)),
                    "simulated_pm": np.exp(np.quantile(sim_h, qs))})
val.to_csv(os.path.join(OUT, "rq4_validation.csv"), index=False)
print(f"validation on {len(hold)} quarters (2025-2026): KS D = {ks.statistic:.3f}, p = {ks.pvalue:.3g}")
print(val.round(1).to_string(index=False))

# 2 scenarios: move one driver from its 10th to its 90th percentile across resampled real profiles
prof = rng.integers(0, len(q), size=NSIM)
kk = rng.integers(0, ndraw, size=NSIM)
scen = []
for d in DRIVERS:
    p10, p90 = np.quantile(q[d], 0.10), np.quantile(q[d], 0.90)
    if p90 - p10 < 1e-9:                         # skewed drivers (AIAD, MSVC): use 0 vs 95th percentile
        p10, p90 = 0.0, np.quantile(q[d], 0.95)
    lo_, hi_ = q[DRIVERS].values[prof].copy(), q[DRIVERS].values[prof].copy()
    j = DRIVERS.index(d); lo_[:, j], hi_[:, j] = p10, p90
    ratio = np.exp(linpred(prof, kk, drivers=hi_) - linpred(prof, kk, drivers=lo_))   # same noise cancels
    per_draw = np.exp(np.array([D[d][i] for i in range(ndraw)]) * (p90 - p10))
    scen.append({"driver": d, "from": p10, "to": p90, "effort_ratio_median": np.median(ratio),
                 "ci90_low": np.quantile(per_draw, 0.05), "ci90_high": np.quantile(per_draw, 0.95)})
scen = pd.DataFrame(scen)
# typical quarter (median size and drivers): effort in PM at low and high levels
med_rows = prof
base = np.exp(linpred(med_rows, kk)).mean()
scen.to_csv(os.path.join(OUT, "rq4_scenarios.csv"), index=False)
print(scen.round(3).to_string(index=False))

# 3 global sensitivity (Sobol) of ln effort to size and the six drivers, posterior-mean coefficients
bounds = [[np.quantile(np.log(q["ksloc"]), 0.05), np.quantile(np.log(q["ksloc"]), 0.95)]]
bounds += [[np.quantile(q[d], 0.05), max(np.quantile(q[d], 0.95), np.quantile(q[d], 0.05) + 1e-6)] for d in DRIVERS]
prob = {"num_vars": 7, "names": ["ln_KSLOC"] + DRIVERS, "bounds": bounds}
X = sobol_sample.sample(prob, 2 ** 13, seed=SEED)
beta = np.r_[D["B"].mean(), [D[d].mean() for d in DRIVERS]]
Y = X @ beta
S = sobol.analyze(prob, Y, seed=SEED)
sob = pd.DataFrame({"input": prob["names"], "S1": S["S1"], "S1_conf": S["S1_conf"], "ST": S["ST"], "ST_conf": S["ST_conf"]})
sob.to_csv(os.path.join(OUT, "rq4_sobol.csv"), index=False)
print(sob.round(3).to_string(index=False))

# 4 bias of a size-only model on simulated projects, by project profile
rows = rng.integers(0, len(q), size=NSIM)
ysim = simulate(rows)
lk = np.log(q["ksloc"].values[rows])
b = np.polyfit(lk, ysim, 1)
err = np.polyval(b, lk) - ysim                  # log error of size-only estimate (positive = overestimate)
v = q.iloc[rows]
groups = {
    "All projects": np.ones(NSIM, bool),
    "High automation (DVOP and CLAU at or above 75th pct)": ((v["DVOP"] >= q["DVOP"].quantile(.75)) & (v["CLAU"] >= q["CLAU"].quantile(.75))).values,
    "Microservices (MSVC above 0)": (v["MSVC"] > 0).values,
    "Experienced team (MTEX at or above 75th pct)": (v["MTEX"] >= q["MTEX"].quantile(.75)).values,
    "New team (MTEX at or below 25th pct)": (v["MTEX"] <= q["MTEX"].quantile(.25)).values,
    "Heavy AI use (AIAD at least 0.3)": (v["AIAD"] >= 0.3).values,
}
bias = pd.DataFrame([{"profile": k, "n": int(m.sum()), "median_ratio_estimate_to_actual": np.exp(np.median(err[m])),
                      "share_off_by_more_than_25pct": 100 * np.mean(np.abs(np.exp(err[m]) - 1) > 0.25)}
                     for k, m in groups.items()])
bias.to_csv(os.path.join(OUT, "rq4_sizeonly_bias.csv"), index=False)
print(bias.round(3).to_string(index=False))

# 5 attenuation of driver effects under measurement error in the driver scores
true = np.array([D[d].mean() for d in DRIVERS])
att = []
for sd in [0.05, 0.10, 0.20]:
    noisy = np.clip(v[DRIVERS].values + rng.normal(0, sd, size=(NSIM, 6)), 0, 1)
    Xn = np.column_stack([np.ones(NSIM), lk, noisy, C[rows]])
    bn, *_ = np.linalg.lstsq(Xn, ysim - rng.normal(0, 0, NSIM), rcond=None)
    Xc = np.column_stack([np.ones(NSIM), lk, v[DRIVERS].values, C[rows]])
    bc, *_ = np.linalg.lstsq(Xc, ysim, rcond=None)
    for j, d in enumerate(DRIVERS):
        att.append({"error_sd": sd, "driver": d, "estimate_no_error": bc[2 + j], "estimate_with_error": bn[2 + j],
                    "retained_pct": 100 * bn[2 + j] / bc[2 + j]})
att = pd.DataFrame(att)
att.to_csv(os.path.join(OUT, "rq4_attenuation.csv"), index=False)
print(att.pivot(index="driver", columns="error_sd", values="retained_pct").round(0).to_string())
