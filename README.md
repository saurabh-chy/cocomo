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
  build_notebook.py  builds notebooks/COCOMO_Extended_pilot.ipynb from the files above
notebooks/           Google Colab notebook(s) to run the pipeline
data/pilot_v1/       first pilot (20 repositories, 6-month windows)
data/pilot_v2/       second pilot (20 repositories, quarterly windows)
docs/                pilot findings, hand-check results and design decisions
```

## How to run

1. Open `notebooks/COCOMO_Extended_pilot.ipynb` in Google Colab.
2. Add a GitHub token as a Colab secret named `GITHUB_TOKEN` (fine-grained, read-only access to public repositories).
3. Run all cells. Results are saved to Google Drive, or to the Colab disk with a download cell at the end.

To change the measurement code, edit the files in `pipeline/` and run `python pipeline/build_notebook.py` to regenerate the notebook.

## Status

- [x] Pilot 1: 20 repositories, measurement problems identified
- [x] Pilot 2: 20 repositories, fixes confirmed
- [x] Hand check of mlflow, go-zero and tinygo against the repositories
- [x] Detection fixes for services and IaC files
- [ ] Full-run notebook (Robles threshold, continuous scores, 2 comparisons per AI repository, contributor screen, batching)
- [ ] OSF pre-registration
- [ ] Full data collection (about 600 repositories)
- [ ] Bayesian model, difference-in-differences, baselines, simulation

See `docs/pilot_log.md` for details. Pilot results are for checking the pipeline only and must not be reported as findings.

## Data sources

All data are public: GitHub repositories and API, the [AIDev dataset](https://huggingface.co/datasets/hao-li/AIDev), and the [OpenSSF Scorecard](https://github.com/ossf/scorecard). The released data contain no developer names or email addresses.
