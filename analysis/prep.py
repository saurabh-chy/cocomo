"""Prepare analysis datasets at two levels from data/full_run.
Outputs (analysis/out/): quarter.csv (included repository-quarters) and repo.csv (one row per repository)."""
import os, glob
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "full_run")
OUT = os.path.join(ROOT, "analysis", "out")
os.makedirs(OUT, exist_ok=True)
DRIVERS = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
MIN_QUARTERS = 4          # repositories need at least 4 included quarters for the repository-level model

d = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(RAW, "repos", "*.csv"))], ignore_index=True)
# AI adoption: first window with any AI signal
sig = (d["agent_merged_prs"].fillna(0) > 0) | (d["ai_commit_share"].fillna(0) > 0) | (d["has_ai_config"] == 1)
d["ai_adopt_start"] = d["repo"].map(d[sig].groupby("repo")["window_start"].min())
d["post_ai"] = (d["ai_adopt_start"].notna() & (d["window_start"] >= d["ai_adopt_start"])).astype(int)
d["company_led_q"] = ((d["owner_type"] == "Organization") & (d["top_corp_domain_share"] >= 0.5)).astype(int)
d["bot_share"] = d["commits_bot"] / d["commits_total"].clip(lower=1)
d["age_years"] = (pd.to_datetime(d["window_start"], utc=True) - pd.to_datetime(d["created_at"], utc=True)).dt.days / 365.25
d["quarter"] = d["window"]
# 9 repositories lack metadata (API lookup failed, e.g. renamed): language 'Unknown', median age
d["language"] = d["language"].fillna("Unknown")
d["age_years"] = d["age_years"].fillna(d.groupby("window")["age_years"].transform("median"))
d.to_csv(os.path.join(OUT, "all_quarters.csv"), index=False)

q = d[(d["include"] == 1) & (d["effort_pm"] > 0) & (d["ksloc"] > 0)].copy()
q["ln_pm"], q["ln_ksloc"] = np.log(q["effort_pm"]), np.log(q["ksloc"])
# company-led as a repository attribute: majority of included quarters
q["company_led"] = q["repo"].map(q.groupby("repo")["company_led_q"].mean() >= 0.5).astype(int)
q.to_csv(os.path.join(OUT, "quarter.csv"), index=False)

agg = {"effort_pm": "sum", "ksloc": "sum", "team_size": "median", "bot_share": "mean", "quarter": "count",
       "language": "first", "group": "first", "company_led": "first", "age_years": "min",
       "ai_adopt_start": "first", "stars": "first"}
agg.update({k: "mean" for k in DRIVERS})
for t in ["effort_pm_t17", "effort_pm_t24", "effort_pm_days"]:
    agg[t] = "sum"
r = q.groupby("repo").agg(agg).rename(columns={"quarter": "n_quarters", "effort_pm": "pm", "ksloc": "ksloc"})
r = r[r["n_quarters"] >= MIN_QUARTERS].reset_index()
r["ln_pm"], r["ln_ksloc"] = np.log(r["pm"]), np.log(r["ksloc"])
r["ln_quarters"] = np.log(r["n_quarters"])
r.to_csv(os.path.join(OUT, "repo.csv"), index=False)
print(f"quarter-level rows: {len(q)} from {q['repo'].nunique()} repositories")
print(f"repository-level rows: {len(r)} (at least {MIN_QUARTERS} included quarters)")
print(r["group"].value_counts().to_dict(), "| company-led:", int(r["company_led"].sum()))
