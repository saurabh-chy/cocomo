# Data dictionary

Files written by `notebooks/COCOMO_Extended_full_run.ipynb` to the `full_run/` results folder.

| File | Contents |
| --- | --- |
| `settings.json` | The rules the run started with; the notebook refuses to continue with different ones |
| `sample.csv` | Selected repositories: group (`ai` / `control`), language, stars, creation date, recent commits, contributors, matched AI repository (controls), first agent PR and number of agent PRs (AI) |
| `repos/<owner>__<name>.csv` | One row per repository-quarter |
| `repos_6m/<owner>__<name>.csv` | Effort and size per 6-month window (robustness check) |
| `dataset_quarterly.csv` | All repository-quarters combined, with AI adoption and company-led flags |
| `dataset_6month_effort.csv` | All 6-month effort rows combined |
| `failures.csv` | Repositories that failed, with the error |

## `dataset_quarterly.csv`

### Identifiers and inclusion

| Column | Meaning |
| --- | --- |
| `repo`, `group` | Repository (`owner/name`) and sample group |
| `window`, `window_start` | Quarter label (e.g. `2025Q3`) and start date |
| `end_commit` | Last commit on the default branch before the window ends; all file-based measures are taken at this commit |
| `include` | 1 if the window has at least 3 core developers (5+ commits) and at least 1 KSLOC of source added |

### Activity, effort and size

| Column | Meaning |
| --- | --- |
| `commits_total`, `commits_human`, `commits_bot`, `commits_ai_author` | Non-merge commits, dated by author date, split by author type |
| `team_size`, `core_devs` | Human developers with at least 1 / at least 5 commits |
| `effort_pm` | **Main effort measure.** Full-time-equivalent developer-months: developers with at least 12 commits per 6 months (6 per quarter) count as full-time, others in proportion (Robles et al. 2022) |
| `effort_pm_t17`, `effort_pm_t24` | Same with thresholds 17 and 24 |
| `effort_pm_days` | Same, counting distinct active days instead of commits |
| `ksloc` | Source lines added (thousands) in non-test, non-generated, non-vendored files, excluding commits that add more than 2,000 source lines |
| `ksloc_test` | Test lines added |
| `ksloc_bulk_excluded`, `n_bulk_commits` | Source lines and commits left out as bulk commits |

### Raw indicators

| Column | Meaning |
| --- | --- |
| `has_ci`, `n_ci_workflows`, `has_test_in_ci`, `ci_change_share` | CI configuration present; number of CI files; a test command in CI; share of commits changing CI files |
| `releases_per_month` | Git tags created per month |
| `merged_prs`, `ci_runs`, `ci_runs_per_week` | From the GitHub API; CI runs are only available for about the last year and are **not** used in the scores |
| `agent_merged_prs`, `agent_pr_share` | Merged agent PRs from AIDev and their share of all merged PRs (blank after AIDev's coverage ends) |
| `ai_commit_share`, `has_ai_config` | Share of non-bot commits written or co-written by AI; AI assistant configuration file present |
| `n_services`, `svc_compose_built`, `svc_k8s_workloads`, `svc_dockerfile_dirs` | Number of services (the highest of the three counts) |
| `n_iac_files`, `iac_change_share`, `ci_deploy` | Infrastructure-as-code files; share of commits changing them; deployment step in CI |
| `tenure_months` | Commit-weighted mean months since each active developer's first commit in the repository |
| `has_security_policy`, `has_dep_update`, `has_sast`, `has_codeowners` | Security practice files and tools |
| `sc_*` | Current OpenSSF Scorecard check scores (0–10), a cross-check only |
| `top_corp_domain`, `top_corp_domain_share` | Most common non-public email domain among human commits and its share (no individual addresses are stored) |
| `stars`, `language`, `created_at`, `owner_type`, `size_mb` | Repository metadata |

### Driver scores (0–1) and levels

| Column | Calculation |
| --- | --- |
| `DVOP` | Mean of: CI present; test step in CI; CI files / 5; releases per month / 2 |
| `AIAD` | Mean of available: agent PR share / 0.30; AI commit share / 0.30; AI config present |
| `MSVC` | log(services) / log(50) |
| `CLAU` | Mean of: IaC present; IaC change share / 0.10; deployment step in CI |
| `MTEX` | Tenure months / 72 |
| `SECU` | Mean of: security policy; dependency-update tool; SAST in CI; CODEOWNERS |
| `<driver>_level` | COCOMO level for reporting only (VL = −2 to XH = 3) |

Each ratio is capped at 1. The main model uses the continuous scores.

### Added when combining

| Column | Meaning |
| --- | --- |
| `ai_adopt_start` | Start of the first window with any AI signal (agent PRs, AI commits or AI config) |
| `post_ai` | 1 from that window on |
| `company_led` | 1 if the owner is an organisation and at least half of human commits come from one corporate email domain |
