"""RQ2 decomposition: does AI adoption change who is active, or how much each person commits?

ln(PM) = ln(active developers) + ln(PM per active developer). Commit-based FTE effort caps each
developer at one full-time month, so it cannot see changes in hours. This script runs the same
staggered difference-in-differences as rq2_did.py on the parts of effort and on commit volume.
Output: out/rq2_components.csv (Table S15).
"""
import os
import numpy as np
import rq2_did as R

q = R.q.copy()
q["ln_team"] = np.log(q["team_size"])
q["ln_core"] = np.log(q["core_devs"].clip(lower=1))
q["ln_pm_per_dev"] = q["ln_pm"] - q["ln_team"]
q["ln_commits_human"] = np.log(q["commits_human"].clip(lower=1))
q["ln_commits_per_dev"] = q["ln_commits_human"] - q["ln_team"]
q["ln_ksloc_per_dev"] = q["ln_ksloc"] - q["ln_team"]

OUT = {
    "ln_team": "Active developers",
    "ln_core": "Core developers",
    "ln_pm_per_dev": "Effort per active developer",
    "ln_commits_human": "Human commits",
    "ln_commits_per_dev": "Human commits per active developer",
    "ln_ksloc_per_dev": "Code per active developer (KSLOC)",
}
rows = []
for y, label in OUT.items():
    r, _ = R.run(q, y, "All")
    r["label"] = label
    rows.append(r)
    pct = lambda v: 100 * (np.exp(v) - 1)
    print(f"{label:38s} ATT {pct(r['att']):+6.1f}% [{pct(r['ci_low']):+6.1f}, {pct(r['ci_high']):+6.1f}]  "
          f"pre {pct(r['pre_avg']):+5.1f}% [{pct(r['pre_ci_low']):+5.1f}, {pct(r['pre_ci_high']):+5.1f}]")
import pandas as pd
pd.DataFrame(rows).to_csv(os.path.join(R.OUT, "rq2_components.csv"), index=False)
