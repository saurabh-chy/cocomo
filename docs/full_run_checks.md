# Full run: completeness and data-quality checks

Results: `data/full_run/` (settings in `settings.json`: theta = 12 commits per 6 months, 200 AI repositories, 2 comparisons each).

## Completeness

| Item | Value |
| --- | --- |
| Repositories processed | 597 of 597 (200 AI, 397 comparison; 3 AI repositories found only one comparison) |
| Failures | none |
| Repository-quarters | 12,583 |
| Quarters meeting the inclusion rules | 5,932 |
| Repositories with at least 8 included quarters | 323 |
| Repositories with no included quarter | 115 |
| Company-led repositories | 351 |
| Languages | TypeScript 185, Go 102, Python 94, C# 89, Java 44, Rust 36, JavaScript 33 |

## AI adoption

| Item | Value |
| --- | --- |
| AI repositories with an AI signal | 100% |
| Comparison repositories with an AI signal during the period | 64% |
| Never-adopting repositories | 141 |
| Adoption quarters with the most repositories | 2025Q2 (108), 2025Q3 (108), 2026Q2 (75), 2026Q1 (66), 2025Q4 (41) |

The staggered difference-in-differences design uses never-adopters and not-yet-adopters as controls.

## Measures (included quarters)

| Variable | Median | 5th to 95th percentile |
| --- | --- | --- |
| Effort (PM per quarter) | 27 | 11 to 111 |
| Size (KSLOC added) | 7.6 | 1.5 to 53 |
| Team size | 16 | 5 to 77 |
| DVOP / AIAD / MSVC / CLAU / MTEX / SECU (median score) | 0.75 / 0 / 0 / 0 / 0.35 / 0.25 | see `dataset_quarterly.csv` |

No missing values in the six driver scores. VIF 1.05 to 1.36. Within-repository SD: DVOP 0.11, AIAD 0.11, MSVC 0.02, CLAU 0.06, MTEX 0.14, SECU 0.11.

## Size-effort relationship

| Unit and definition | n | Pooled exponent B | R-squared | Random-intercept B |
| --- | --- | --- | --- | --- |
| Quarter, KSLOC (main) | 5,932 | 0.38 | 0.30 | 0.21 |
| Quarter, KSLOC including tests | 5,932 | 0.40 | 0.33 | 0.20 |
| Quarter, effort with theta = 24 | 5,932 | 0.42 | 0.37 | 0.25 |
| Quarter, effort by active days | 5,932 | 0.40 | 0.31 | 0.22 |
| 6-month windows (KSLOC at least 2) | 4,717 | 0.50 | 0.30 | 0.27 |
| **Repository totals over the study period** | **482** | **0.75** | **0.72** | - |

**Correction (after the analysis):** the repository-total exponent of 0.75 is an artefact of observation length. Total effort and total size both grow with the number of quarters a repository is observed, which the study window sets. With the number of observed quarters controlled, the repository-level exponent is 0.27 (Bayesian model, `analysis/out/rq1_repo_literature_duration.csv`). Code size is a weak predictor of effort at both levels; effort tracks team size (correlation of log effort and log team size: 0.94).

Decision: the repository-level model controls for the number of observed quarters (main specification). The model without that control is reported only to show the artefact.
