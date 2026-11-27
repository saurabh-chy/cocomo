"""Robustness of the repository-quarter model (frequentist mixed model with random repository intercepts):
alternative effort measures and company-led vs community repositories. Also descriptive tables."""
import os, warnings
import numpy as np, pandas as pd, statsmodels.formula.api as smf
warnings.filterwarnings("ignore")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
DR = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
q = pd.read_csv(os.path.join(OUT, "quarter.csv"))
q["age_z"] = (q["age_years"] - q["age_years"].mean()) / q["age_years"].std()
rhs = "ln_ksloc + " + " + ".join(DR) + " + C(language) + company_led + age_z + bot_share + C(quarter)"

def mixed(df, y, label):
    f = rhs if df["company_led"].nunique() > 1 else rhs.replace(" + company_led", "")
    m = smf.mixedlm(f"{y} ~ {f}", df, groups=df["repo"]).fit(reml=True, method="lbfgs")
    row = {"variant": label, "n": len(df), "repos": df["repo"].nunique()}
    for k in ["ln_ksloc"] + DR:
        row[k] = m.params[k]; row[k + "_se"] = m.bse[k]
    return row

rows = []
for y, label in [("ln_pm", "Main (theta = 12)"), ("ln_t17", "Effort, theta = 17"), ("ln_t24", "Effort, theta = 24"),
                 ("ln_days", "Effort, active days")]:
    q["ln_t17"], q["ln_t24"], q["ln_days"] = np.log(q["effort_pm_t17"]), np.log(q["effort_pm_t24"]), np.log(q["effort_pm_days"])
    rows.append(mixed(q, y, label))
rows.append(mixed(q[q["company_led"] == 1], "ln_pm", "Company-led repositories"))
rows.append(mixed(q[q["company_led"] == 0], "ln_pm", "Community repositories"))
rob = pd.DataFrame(rows)
rob.to_csv(os.path.join(OUT, "robustness.csv"), index=False)
print(rob[["variant", "n", "repos", "ln_ksloc"] + DR].round(3).to_string(index=False))

# descriptive statistics of included repository-quarters
desc = q[["effort_pm", "ksloc", "team_size"] + DR].describe(percentiles=[0.05, 0.5, 0.95]).T
desc = desc[["mean", "50%", "std", "5%", "95%"]]
desc.to_csv(os.path.join(OUT, "descriptives.csv"))
print(desc.round(2).to_string())
corr = q[DR].corr(); corr.to_csv(os.path.join(OUT, "driver_corr.csv")); print(corr.round(2).to_string())
r = pd.read_csv(os.path.join(OUT, "repo.csv"))
print("repo level:", len(r), r["group"].value_counts().to_dict(), "median quarters", r["n_quarters"].median())
print("quarter level by group:", q.groupby("group")["repo"].nunique().to_dict(), q["group"].value_counts().to_dict())
print("company-led repos (quarter sample):", q.groupby("repo")["company_led"].first().sum())
print("language:", q.groupby("repo")["language"].first().value_counts().to_dict())
