"""RQ3: estimation accuracy. Repository-quarter rows; 10-fold cross-validation grouped by repository,
so every test repository is new to the model (the situation of estimating a new project)."""
import os
import numpy as np, pandas as pd
from scipy.stats import wilcoxon
from sklearn.ensemble import RandomForestRegressor

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
DRIVERS = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
PRIOR_MEAN = {"DVOP": np.log(0.78 / 1.17), "CLAU": np.log(0.78 / 1.17), "MTEX": np.log(0.81 / 1.22),
              "SECU": np.log(1.26 / 0.82), "MSVC": 0.0, "AIAD": 0.0}
PRIOR_SD = {"DVOP": 0.3, "CLAU": 0.3, "MTEX": 0.3, "SECU": 0.3, "MSVC": 0.5, "AIAD": 0.5}
SEED, K, Z90 = 20261127, 10, 1.6449

q = pd.read_csv(os.path.join(OUT, "quarter.csv"))
ctrl = pd.get_dummies(q["language"], prefix="lang", drop_first=True, dtype=float)
ctrl = ctrl.join(pd.get_dummies(q["quarter"], prefix="q", drop_first=True, dtype=float))
ctrl["company_led"] = q["company_led"].astype(float)
ctrl["age_years"] = q["age_years"]
ctrl["bot_share"] = q["bot_share"]
y, pm_, ks = q["ln_pm"].values, q["effort_pm"].values, q["ksloc"].values

def ols(X, yv):
    b, *_ = np.linalg.lstsq(X, yv, rcond=None)
    s2 = np.sum((yv - X @ b) ** 2) / max(1, len(yv) - X.shape[1])
    return b, s2

def bayes_lin(X, yv, mu0, prec0):
    """Posterior mean and covariance of a linear model with Gaussian priors (residual variance plugged in)."""
    _, s2 = ols(X, yv)
    A = X.T @ X / s2 + np.diag(prec0)
    cov = np.linalg.inv(A)
    return cov @ (X.T @ yv / s2 + prec0 * mu0), cov, s2

rng = np.random.default_rng(SEED)
repos = q["repo"].unique()
fold_of = dict(zip(repos, rng.permutation(len(repos)) % K))
fold = q["repo"].map(fold_of).values
pred = {m: np.full(len(q), np.nan) for m in ["COCOMO II (default)", "Size-only (linear)", "COCOMO II (recalibrated)",
                                             "ATLM", "Random forest", "COCOMO-Extended"]}
lo, hi = {m: np.full(len(q), np.nan) for m in pred}, {m: np.full(len(q), np.nan) for m in pred}
p0 = []                                 # random-guessing MAEs for Standardized Accuracy

for f in range(K):
    tr, te = fold != f, fold == f
    one = lambda m: np.ones((m.sum(), 1))
    # 1 COCOMO II.2000 nominal: PM = 2.94 * KSLOC^1.0997 (all multipliers nominal)
    pred["COCOMO II (default)"][te] = 2.94 * ks[te] ** 1.0997
    # 2 size-only linear regression on the raw scale
    X = np.column_stack([one(tr), ks[tr]]); b, s2 = ols(X, pm_[tr])
    Xt = np.column_stack([one(te), ks[te]]); pred["Size-only (linear)"][te] = Xt @ b
    lo["Size-only (linear)"][te] = Xt @ b - Z90 * np.sqrt(s2); hi["Size-only (linear)"][te] = Xt @ b + Z90 * np.sqrt(s2)
    # 3 COCOMO II recalibrated: ln PM = ln A + B ln KSLOC
    X = np.column_stack([one(tr), np.log(ks[tr])]); b, s2 = ols(X, y[tr])
    Xt = np.column_stack([one(te), np.log(ks[te])])
    for m, B_ in [("COCOMO II (recalibrated)", (b, s2))]:
        mu = Xt @ B_[0]; pred[m][te] = np.exp(mu)
        lo[m][te], hi[m][te] = np.exp(mu - Z90 * np.sqrt(B_[1])), np.exp(mu + Z90 * np.sqrt(B_[1]))
    # 4 ATLM: log-transformed size plus all conventional attributes (no new drivers)
    Xc = ctrl.values
    X = np.column_stack([one(tr), np.log(ks[tr]), Xc[tr]]); b, s2 = ols(X, y[tr])
    Xt = np.column_stack([one(te), np.log(ks[te]), Xc[te]]); mu = Xt @ b
    pred["ATLM"][te] = np.exp(mu); lo["ATLM"][te], hi["ATLM"][te] = np.exp(mu - Z90 * np.sqrt(s2)), np.exp(mu + Z90 * np.sqrt(s2))
    # 5 random forest on ln effort with all inputs
    F = np.column_stack([np.log(ks), q[DRIVERS].values, Xc])
    rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=5, n_jobs=2, random_state=SEED).fit(F[tr], y[tr])
    pred["Random forest"][te] = np.exp(rf.predict(F[te]))
    # 6 COCOMO-Extended: Bayesian linear model, literature priors on the drivers
    X = np.column_stack([one(tr), np.log(ks[tr]), q[DRIVERS].values[tr], Xc[tr]])
    Xt = np.column_stack([one(te), np.log(ks[te]), q[DRIVERS].values[te], Xc[te]])
    mu0 = np.r_[0, 1.0, [PRIOR_MEAN[k] for k in DRIVERS], np.zeros(Xc.shape[1])]
    prec0 = np.r_[1 / 25, 1 / 0.25, [1 / PRIOR_SD[k] ** 2 for k in DRIVERS], np.ones(Xc.shape[1]) / 100]
    bm, cov, s2 = bayes_lin(X, y[tr], mu0, prec0)
    mu = Xt @ bm; sd = np.sqrt(s2 + np.einsum("ij,jk,ik->i", Xt, cov, Xt))
    pred["COCOMO-Extended"][te] = np.exp(mu)
    lo["COCOMO-Extended"][te], hi["COCOMO-Extended"][te] = np.exp(mu - Z90 * sd), np.exp(mu + Z90 * sd)
    # random guessing: predict each test case with the effort of a random training case
    for _ in range(100):
        p0.append(np.abs(pm_[te] - rng.choice(pm_[tr], size=te.sum())))

p0 = np.array([np.mean(np.concatenate(p0[i::100])) for i in range(100)])   # 100 full random-guessing runs
mae_p0, sd_p0 = p0.mean(), p0.std(ddof=1)
rows, ae = [], {}
for m, p in pred.items():
    e = np.abs(pm_ - p); ae[m] = e
    cov90 = np.mean((pm_ >= lo[m]) & (pm_ <= hi[m])) if not np.all(np.isnan(lo[m])) else np.nan
    rows.append({"model": m, "MAE": e.mean(), "MdAE": np.median(e), "SA_pct": 100 * (1 - e.mean() / mae_p0),
                 "glass_delta": (mae_p0 - e.mean()) / sd_p0, "pred25": 100 * np.mean(e / pm_ <= 0.25),
                 "pi90_coverage": 100 * cov90 if not np.isnan(cov90) else np.nan})
res = pd.DataFrame(rows)

def a12(x, y_):
    """Vargha-Delaney A: probability that a value from x exceeds one from y."""
    r = pd.Series(np.r_[x, y_]).rank().values
    return (r[:len(x)].sum() / len(x) - (len(x) + 1) / 2) / len(y_)

tests = []
for m in pred:
    if m == "COCOMO-Extended":
        continue
    p = wilcoxon(ae[m], ae["COCOMO-Extended"]).pvalue
    tests.append({"baseline": m, "p": p, "A12": a12(ae[m], ae["COCOMO-Extended"])})
tests = pd.DataFrame(tests).sort_values("p").reset_index(drop=True)
k = len(tests)
tests["p_holm"] = np.minimum(1, np.maximum.accumulate(tests["p"] * (k - np.arange(k))))
res.to_csv(os.path.join(OUT, "rq3_accuracy.csv"), index=False)
tests.to_csv(os.path.join(OUT, "rq3_tests.csv"), index=False)
print(f"random guessing MAE = {mae_p0:.2f} PM (SD {sd_p0:.3f})")
print(res.round(2).to_string(index=False))
print(tests.round(4).to_string(index=False))
