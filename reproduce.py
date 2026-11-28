"""Reproduce every computed table and figure of the paper from the collected data.

    python reproduce.py               # full run (Bayesian models take the longest)
    python reproduce.py --skip-bayes  # reuse posterior draws already in analysis/out/*_draws.npz

Input: data/full_run/ (the mined repository data). Output:
    analysis/tables/Table_*.csv and analysis/tables/all_tables.xlsx  (Tables 2-10, S6-S9, S11-S15)
    analysis/figures/figure1-4*.png                                   (Figures 1-4)
Intermediate results go to analysis/out/. Seeds are fixed, so a rerun gives the same numbers on the
same package versions (requirements.txt); MCMC draws may differ slightly on other versions.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
AN = os.path.join(HERE, "analysis")

STEPS = [
    ("prep.py", "Build repository-quarter and repository datasets", ""),
    ("rq1_bayes.py", "RQ1 Bayesian models at both levels (posterior draws)", "Tables 5, S6, S7; Figure 2"),
    ("robustness.py", "Robustness models and descriptive statistics", "Tables 4, 6"),
    ("audit_checks.py", "Within/between split, turnover control, DiD without inclusion rules", "Tables 6, 7, S8"),
    ("rq2_did.py", "RQ2 staggered difference-in-differences", "Table 7, S9; Figure 3"),
    ("rq2_components.py", "RQ2 on the parts of effort", "Table S15"),
    ("rq2_treatment.py", "RQ2 under alternative adoption definitions", "Table S16"),
    ("effort_construct.py", "What the effort measure counts", "Table S14"),
    ("rq3_accuracy.py", "RQ3 grouped 10-fold cross-validation", "Tables 8, S17"),
    ("rq4_sim.py", "RQ4 simulator, Sobol indices, scenarios", "Tables 9, 10, S11-S13; Figure 4"),
    ("figures.py", "Figures 1-4", "Figures 1-4"),
    ("make_tables.py", "Format all tables as in the paper", "all tables"),
]

if __name__ == "__main__":
    skip_bayes = "--skip-bayes" in sys.argv
    for script, what, feeds in STEPS:
        if skip_bayes and script == "rq1_bayes.py":
            print(f"-- skipping {script} (using existing draws)")
            continue
        print(f"\n== {script}: {what}" + (f"  -> {feeds}" if feeds else ""), flush=True)
        t = time.time()
        subprocess.run([sys.executable, script], cwd=AN, check=True)
        print(f"   done in {time.time() - t:.0f} s")
    print("\nTables: analysis/tables/   Figures: analysis/figures/")
