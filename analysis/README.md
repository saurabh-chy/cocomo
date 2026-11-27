# Analysis

Run everything with `python reproduce.py` from the repository root, or run the scripts below in order from this folder (Python 3 with pymc, arviz, statsmodels, scikit-learn, SALib, matplotlib):

| Script | Purpose | Main outputs (analysis/out/) |
| --- | --- | --- |
| `prep.py` | Builds the repository-quarter and repository datasets from `data/full_run/` | `quarter.csv`, `repo.csv` |
| `rq1_bayes.py` | RQ1: Bayesian COCOMO-style models at both levels, literature and vague priors | `rq1_*.csv`, `rq1_*_draws.npz` |
| `rq2_did.py` | RQ2: staggered difference-in-differences (Callaway & Sant'Anna), clustered bootstrap | `rq2_att.csv`, `rq2_event_study.csv` |
| `rq3_accuracy.py` | RQ3: six models, grouped 10-fold cross-validation | `rq3_accuracy.csv`, `rq3_tests.csv` |
| `rq4_sim.py` | RQ4: simulator built from the fitted quarter model | `rq4_*.csv` |
| `robustness.py` | Alternative effort measures, company-led vs community, descriptives | `robustness.csv`, `descriptives.csv` |
| `figures.py` | Figures 1-4 of the paper | `analysis/figures/*.png` |
| `audit_checks.py` | Within/between split, turnover control, DiD without inclusion rules, Scorecard check | `audit_checks.csv`, `rq2_att_unfiltered.csv` |
| `effort_construct.py` | What the effort measure counts | `effort_construct.csv` |
| `rq2_components.py` | RQ2 on the parts of effort | `rq2_components.csv` |
| `make_tables.py` | Formats every computed table as printed in the paper | `analysis/tables/Table_*.csv`, `all_tables.xlsx` |

Seeds are fixed (20261127). The posterior draw files (`*.npz`) are large and not committed; rerun `rq1_bayes.py` to recreate them.
