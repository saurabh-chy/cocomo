# COCOMO-Extended

Data-collection and analysis code for the study **"COCOMO-Extended: Calibrating Contemporary Cost Drivers from Open-Source Repository Data"** (target journal: *Journal of Software: Evolution and Process*).

The study extends COCOMO II with six contemporary cost drivers and estimates their effect on development effort from public GitHub data:

| Code | Driver | Measured from |
| --- | --- | --- |
| DVOP | DevOps maturity | CI configuration files, test steps in CI, release frequency (git tags) |
| AIAD | AI-agent assistance | Agent-authored PRs (AIDev dataset), AI-authored or AI-co-authored commits, AI assistant config files |
| MSVC | Microservice complexity | Services with their own Dockerfile and build file, unique Kubernetes workloads, docker-compose services built from source |
| CLAU | Cloud automation | IaC files in deployment folders, share of commits touching them, deployment steps in CI |
| MTEX | Team experience | Commit-weighted months since each active developer's first commit in the repository |
| SECU | Security practices | SECURITY.md, Dependabot/Renovate, CODEOWNERS, SAST in CI (OpenSSF Scorecard kept as a cross-check) |

Effort is full-time-equivalent developer-months following Robles et al. (2022, *Empirical Software Engineering*). Size is source lines added in each window, excluding test, generated and vendored files and bulk commits.

## Repository layout

```
pipeline/            measurement code (also embedded in the notebook)
  core.py            git-based measures: effort, size, the six drivers
  api.py             GitHub API, OpenSSF Scorecard and AIDev helpers
  run.py             per-repository processing and driver scoring
  select.py          sample selection (AI repositories and matched comparisons)
  build_notebook.py  builds notebooks/COCOMO_Extended_full_run.ipynb from the files above
notebooks/
  COCOMO_Extended_full_run.ipynb   the notebook for the main data collection
  COCOMO_Extended_pilot.ipynb      pilot version, kept as a record
data/full_run/       main collection: 597 repositories, one file per repository and quarter
data/Supplementary_Data_S1_repositories.csv   repository list (Supplementary Data S1)
analysis/            analysis scripts; out/ intermediate results, tables/ and figures/ the paper's tables and figures
reproduce.py         runs the whole analysis and rebuilds every table and figure
data/pilot_v1/       first pilot (20 repositories, 6-month windows)
data/pilot_v2/       second pilot (20 repositories, quarterly windows)
docs/
  pilot_log.md       pilot findings, hand-check results and design decisions
  data_dictionary.md every output file and column
```

## Reproduce the tables and figures

Needs Python 3.11 or later and the packages in `requirements.txt`. The mined data are already in `data/full_run/`, so no GitHub token is needed.

```bash
pip install -r requirements.txt
python reproduce.py               # full run; the Bayesian models take the longest
python reproduce.py --skip-bayes  # faster: reuse posterior draws already in analysis/out/
```

| Output | Files | Made by |
| --- | --- | --- |
| Table 2 (sample) | `analysis/tables/Table_2.csv` | `prep.py`, `make_tables.py` |
| Table 3 (priors) | `Table_3.csv` | constants in `rq1_bayes.py` |
| Table 4 (descriptives) | `Table_4.csv` | `robustness.py` |
| Table 5, Tables S6-S7 (driver effects) | `Table_5.csv`, `Table_S6.csv`, `Table_S7.csv` | `rq1_bayes.py` |
| Table 6, Table S8 (robustness) | `Table_6.csv`, `Table_S8.csv` | `robustness.py`, `audit_checks.py` |
| Table 7, Table S9 (AI adoption) | `Table_7.csv`, `Table_S9.csv` | `rq2_did.py`, `audit_checks.py` |
| Table 8 (accuracy) | `Table_8.csv` | `rq3_accuracy.py` |
| Tables 9-10, S11-S13 (simulation) | `Table_9.csv`, `Table_10.csv`, `Table_S11.csv` ... | `rq4_sim.py` |
| Table S14 (effort measure) | `Table_S14.csv` | `effort_construct.py` |
| Table S15 (AI and the parts of effort) | `Table_S15.csv` | `rq2_components.py` |
| Figures 1-4 | `analysis/figures/figure1_size_effort.png` ... `figure4_scenarios.png` | `figures.py` |

All tables are also collected in `analysis/tables/all_tables.xlsx`. Tables 1, S1-S3 and S10 state measurement rules and simulator inputs; the rules are coded in `pipeline/core.py` and `pipeline/run.py`, the inputs in `analysis/rq4_sim.py`. Tables S4-S5 report the pilots and the hand check (`docs/pilot_log.md`).

## Collect the data again

1. Open `notebooks/COCOMO_Extended_full_run.ipynb` in Google Colab.
2. Add a GitHub token as a Colab secret named `GITHUB_TOKEN` (fine-grained, read-only access to public repositories).
3. Run all cells. The full run (about 600 repositories) takes several sessions: each session stops after its time budget, and running the notebook again continues where it stopped. Use Google Drive so results persist between sessions.

To change the measurement code, edit the files in `pipeline/` and run `python pipeline/build_notebook.py` to regenerate the notebook.

## Status

- [x] Pilot 1: 20 repositories, measurement problems identified
- [x] Pilot 2: 20 repositories, fixes confirmed
- [x] Hand check of mlflow, go-zero and tinygo against the repositories
- [x] Detection fixes for services and IaC files
- [x] Full-run notebook (Robles threshold, continuous scores, 2 comparisons per AI repository, contributor screen, resumable batches)
- [x] Full data collection: 597 repositories, 12,583 repository-quarters (see docs/full_run_checks.md)
- [x] Bayesian models, difference-in-differences, baselines, simulation (analysis/)
- [x] Reproduction script for every computed table and figure (reproduce.py)

See `docs/pilot_log.md` for details. Pilot results are for checking the pipeline only and must not be reported as findings.

## Data sources

All data are public: GitHub repositories and API, the [AIDev dataset](https://huggingface.co/datasets/hao-li/AIDev), and the [OpenSSF Scorecard](https://github.com/ossf/scorecard). The released data contain no developer names or email addresses.
