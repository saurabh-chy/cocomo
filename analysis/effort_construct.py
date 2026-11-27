"""How much of commit-based FTE effort is a head count?

The Robles et al. (2022) measure sums min(1, commits/theta) over developers, so
effort is close to a weighted count of active developers. This script splits
ln(PM) into ln(active developers) + ln(PM per active developer) and reports how
each part relates to size, pooled and within repositories. Output:
out/effort_construct.csv (used for Table S14 and Sections 5.1 and 6.1).
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

HERE = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
q = pd.read_csv(f"{HERE}/out/quarter.csv")
q["ln_team"] = np.log(q.team_size)
q["ln_int"] = q.ln_pm - q.ln_team          # person-months per active developer

w = q.copy()
for c in ["ln_pm", "ln_team", "ln_ksloc", "ln_int"]:
    w[c] = w[c] - w.groupby("repo")[c].transform("mean")

rows = []
specs = [
    ("Effort on active developers", "ln_pm ~ ln_team", "ln_team"),
    ("Effort on size", "ln_pm ~ ln_ksloc", "ln_ksloc"),
    ("Active developers on size", "ln_team ~ ln_ksloc", "ln_ksloc"),
    ("Effort per developer on size", "ln_int ~ ln_ksloc", "ln_ksloc"),
]
for label, f, term in specs:
    for level, data, formula in [("Pooled", q, f), ("Within repository", w, f + " - 1")]:
        m = smf.ols(formula, data).fit(cov_type="cluster", cov_kwds={"groups": data.repo.astype("category").cat.codes})
        lo, hi = m.conf_int().loc[term]
        rows.append(dict(model=label, level=level, slope=m.params[term], ci_lo=lo, ci_hi=hi, r2=m.rsquared))

out = pd.DataFrame(rows)
out.to_csv(f"{HERE}/out/effort_construct.csv", index=False)
print(out.round(3).to_string(index=False))
print("median PM per active developer per quarter:", round((q.effort_pm / q.team_size).median(), 2), "(ceiling 3)")
print("within-repo SD: ln_team", round(w.ln_team.std(), 3), "ln_ksloc", round(w.ln_ksloc.std(), 3), "ln_pm", round(w.ln_pm.std(), 3))
