"""RQ1: Bayesian COCOMO-style models at the repository level and the repository-quarter level.
Each is fitted with literature-based priors and with vague priors."""
import os, json, sys
import numpy as np, pandas as pd, pymc as pm, arviz as az

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
DRIVERS = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
# Literature priors on the full-range effect (score 0 -> 1) on ln(effort):
# DVOP, CLAU: COCOMO II TOOL, VL 1.17 -> VH 0.78; MTEX: APEX, VL 1.22 -> VH 0.81;
# SECU: RELY, VL 0.82 -> VH 1.26; MSVC, AIAD: no calibrated prior (centred on 0).
PRIOR_MEAN = {"DVOP": np.log(0.78 / 1.17), "CLAU": np.log(0.78 / 1.17), "MTEX": np.log(0.81 / 1.22),
              "SECU": np.log(1.26 / 0.82), "MSVC": 0.0, "AIAD": 0.0}
PRIOR_SD = {"DVOP": 0.3, "CLAU": 0.3, "MTEX": 0.3, "SECU": 0.3, "MSVC": 0.5, "AIAD": 0.5}
SEED = 20261127

def design(df, level, duration=False):
    X = pd.get_dummies(df["language"], prefix="lang", drop_first=True, dtype=float)
    X["company_led"] = df["company_led"].astype(float)
    X["age_years"] = (df["age_years"] - df["age_years"].mean()) / df["age_years"].std()
    X["bot_share"] = df["bot_share"]
    if level == "repo":
        if duration:      # observation length: totals accumulate over the quarters the study observes
            X["ln_quarters"] = df["ln_quarters"] - df["ln_quarters"].mean()
    else:
        X = X.join(pd.get_dummies(df["quarter"], prefix="q", drop_first=True, dtype=float))
    return X

def fit(level, prior, duration=False):
    df = pd.read_csv(os.path.join(OUT, f"{level}.csv"))
    C = design(df, level, duration)
    lk = df["ln_ksloc"].values
    lk_c = lk - lk.mean()
    with pm.Model() as m:
        a = pm.Normal("lnA", 0, 5)
        B = pm.Normal("B", 1.0, 0.5) if prior == "literature" else pm.Normal("B", 0, 10)
        g = {k: (pm.Normal(k, PRIOR_MEAN[k], PRIOR_SD[k]) if prior == "literature" else pm.Normal(k, 0, 10))
             for k in DRIVERS}
        bc = pm.Normal("controls", 0, 1, shape=C.shape[1])
        mu = a + B * lk_c + sum(g[k] * df[k].values for k in DRIVERS) + pm.math.dot(C.values, bc)
        if level == "quarter":
            codes, uniq = pd.factorize(df["repo"])
            s_u = pm.HalfNormal("sigma_repo", 1)
            z = pm.Normal("z_repo", 0, 1, shape=len(uniq))
            mu = mu + s_u * z[codes]
        s = pm.HalfNormal("sigma", 1)
        pm.Normal("y", mu, s, observed=df["ln_pm"].values)
        n = 3000 if level == "quarter" else 1000        # longer chains for the multilevel model
        idata = pm.sample(n, tune=n, chains=4, cores=4, random_seed=SEED, progressbar=False,
                          target_accept=0.95)
        pm.sample_posterior_predictive(idata, extend_inferencedata=True, random_seed=SEED, progressbar=False)
    names = ["B"] + DRIVERS + ["sigma"] + (["sigma_repo"] if level == "quarter" else [])
    sm = az.summary(idata, var_names=names, ci_prob=0.95)
    sm.to_csv(os.path.join(OUT, f"rq1_{level}_{prior}{'_duration' if duration else ''}.csv"))
    post = idata.posterior
    draws = {v: post[v].values.reshape(-1, *post[v].shape[2:]) for v in ["lnA", "B", "sigma", "controls"] + DRIVERS
             + (["sigma_repo"] if level == "quarter" else [])}
    np.savez_compressed(os.path.join(OUT, f"rq1_{level}_{prior}{'_duration' if duration else ''}_draws.npz"), **draws,
                        control_names=np.array(C.columns), lk_mean=lk.mean())
    # Bayesian R2 (proportion of variance explained by the linear predictor)
    print(f"\n== {level} / {prior} / duration={duration}: n={len(df)}; max R-hat {sm['r_hat'].max():.3f}; "
          f"min ESS {sm['ess_bulk'].min():.0f}")
    print(sm[["mean", "sd", "eti95_lb", "eti95_ub", "r_hat"]].round(3).to_string())
    return sm

if __name__ == "__main__":
    levels = sys.argv[1:] or ["repo", "quarter"]
    for level in levels:
        main_dur = (level == "repo")     # repository level: control for observation length (main spec)
        for prior in ["literature", "vague"]:
            fit(level, prior, duration=main_dur)
        if level == "repo":
            fit(level, "literature", duration=False)   # illustration: without the control, totals are confounded
