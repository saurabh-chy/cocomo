"""Audit checks run after the first draft:
1 within-repository vs between-repository effects (Mundlak decomposition)
2 mechanical links between drivers and the effort measure (team churn, activity)
3 difference-in-differences without the inclusion filter (selection check)
4 security score vs OpenSSF Scorecard (convergent validity)"""
import os, warnings, sys
import numpy as np, pandas as pd, statsmodels.formula.api as smf
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
sys.path.insert(0, HERE)
DR = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
q = pd.read_csv(os.path.join(OUT, "quarter.csv"))
q["age_z"] = (q["age_years"] - q["age_years"].mean()) / q["age_years"].std()
base = "ln_ksloc + C(language) + company_led + age_z + bot_share + C(quarter)"
rows = []

# 1 Mundlak: driver = within part (deviation from repository mean) + between part (repository mean)
for d in DR + ["ln_ksloc"]:
    q[d + "_m"] = q.groupby("repo")[d].transform("mean")
    q[d + "_w"] = q[d] - q[d + "_m"]
f = ("ln_pm ~ ln_ksloc_w + ln_ksloc_m + " + " + ".join(f"{d}_w + {d}_m" for d in DR) +
     " + C(language) + company_led + age_z + bot_share + C(quarter)")
m = smf.mixedlm(f, q, groups=q["repo"]).fit(reml=True, method="lbfgs")
print("1 Mundlak decomposition (effort ratio over the full 0-1 range; 95% CI)")
for d in ["ln_ksloc"] + DR:
    for part in ["w", "m"]:
        k = f"{d}_{part}"; b, se = m.params[k], m.bse[k]
        val = (f"{b:.3f} ({b-1.96*se:.3f}, {b+1.96*se:.3f})" if d == "ln_ksloc"
               else f"{np.exp(b):.2f} ({np.exp(b-1.96*se):.2f}, {np.exp(b+1.96*se):.2f})")
        print(f"   {d:8s} {'within ' if part=='w' else 'between'}: {val}")
        rows.append({"check": "mundlak", "term": d, "part": part, "coef": b, "se": se})

# 2 mechanical links: share of non-core contributors (drive-by developers) and activity
q["noncore_share"] = 1 - q["core_devs"] / q["team_size"]
print("\n2 correlations with log effort and with team churn")
print(q[["ln_pm", "noncore_share", "MTEX", "DVOP", "CLAU", "releases_per_month"]].corr().round(2).to_string())
m2 = smf.mixedlm("ln_pm ~ " + " + ".join(DR) + " + noncore_share + " + base, q, groups=q["repo"]).fit(reml=True, method="lbfgs")
m1 = smf.mixedlm("ln_pm ~ " + " + ".join(DR) + " + " + base, q, groups=q["repo"]).fit(reml=True, method="lbfgs")
print("   effort ratios without / with control for share of non-core contributors:")
for d in DR:
    print(f"   {d}: {np.exp(m1.params[d]):.2f} / {np.exp(m2.params[d]):.2f}")
    rows.append({"check": "noncore_control", "term": d, "coef": m2.params[d], "se": m2.bse[d]})

# 3 DiD without the inclusion filter (all quarters with effort > 0 and size > 0)
import importlib.util
spec = importlib.util.spec_from_file_location("did", os.path.join(HERE, "rq2_did.py"))
did = importlib.util.module_from_spec(spec)
a = pd.read_csv(os.path.join(OUT, "all_quarters.csv"))
a = a[(a["effort_pm"] > 0) & (a["ksloc"] > 0)].copy()
a["ln_pm"], a["ln_ksloc"] = np.log(a["effort_pm"]), np.log(a["ksloc"])
a["ln_prod"] = a["ln_ksloc"] - a["ln_pm"]
a["company_led"] = 0
a.to_csv(os.path.join(OUT, "_tmp_all.csv"), index=False)
src = open(os.path.join(HERE, "rq2_did.py")).read().split('if __name__ == "__main__":')[0]
src = src.replace('os.path.join(OUT, "quarter.csv")', 'os.path.join(OUT, "_tmp_all.csv")')
ns = {"__file__": os.path.join(HERE, "rq2_did.py")}
exec(src, ns)
print("\n3 DiD on all quarters with effort and size > 0 (no inclusion filter)")
unf = []
for y in ["ln_pm", "ln_ksloc", "ln_prod"]:
    r, _ = ns["run"](ns["q"], y, "unfiltered")
    pct = lambda v: 100 * (np.exp(v) - 1)
    print(f"   {y:9s} {pct(r['att']):+.1f}% ({pct(r['ci_low']):+.1f}, {pct(r['ci_high']):+.1f}); pre {pct(r['pre_avg']):+.1f}%; "
          f"adopters {r['n_treated_repos']}, never {r['n_never']}")
    unf.append(r)
    rows.append({"check": "did_unfiltered", "term": y, "coef": r["att"], "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                 "pre": r["pre_avg"], "n_treated": r["n_treated_repos"], "n_never": r["n_never"]})
os.remove(os.path.join(OUT, "_tmp_all.csv"))
pd.DataFrame(unf).to_csv(os.path.join(OUT, "rq2_att_unfiltered.csv"), index=False)   # Table 7, last three rows

# 4 SECU vs OpenSSF Scorecard (current scores; compare with the repository's latest SECU)
sc = [c for c in q.columns if c.startswith("sc_")]
last = q.sort_values("quarter").groupby("repo").tail(1)
last = last.assign(scorecard=last[sc].mean(axis=1) / 10)
ok = last.dropna(subset=["scorecard"])
rho = ok[["SECU", "scorecard"]].corr(method="spearman").iloc[0, 1]
print(f"\n4 Spearman correlation of latest SECU with current Scorecard mean: {rho:.2f} (n = {len(ok)} repositories)")
rows.append({"check": "scorecard", "term": "SECU", "coef": rho, "n_treated": len(ok)})
pd.DataFrame(rows).to_csv(os.path.join(OUT, "audit_checks.csv"), index=False)
