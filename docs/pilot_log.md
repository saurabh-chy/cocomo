# Pilot log and design decisions

Pilot results are for checking the pipeline only. They are not findings and must not be reported in the paper.

## Pilot 1 (20 repositories, 6-month windows, 2021H1 to 2026H1)

Data: `data/pilot_v1/`

| Problem | Evidence | Fix (pilot 2) |
| --- | --- | --- |
| Many inactive or non-software repositories | Only 104 of 211 windows met the inclusion rules; 7 repositories had 0 to 2 usable windows; one was a data repository | Activity screen before cloning (300+ commits since 2025-01-01); minimum 1 KSLOC per window |
| CI-run counts missing before 2025H2 | All windows before 2025H2 had zero CI runs: the GitHub API keeps run history for about one year | DevOps maturity measured from git: CI files, test steps, release tags |
| Size hardly explained effort | Size exponent 0.41 pooled, 0.19 within repositories; bulk code drops (lakeFS: 225 KSLOC with 35 PM) | Commits adding more than 2,000 source lines excluded from size and recorded separately |
| Few periods after AI adoption | Most AI repositories adopted agents in late 2025 or 2026 | Quarterly windows; AI repositories must adopt by 2025-09-30 |
| Comparison repositories adopting AI | kiali and RedisInsight used AI in 2026H1 | Adoption defined by any AI signal; staggered design treats them as later adopters |

Test of the size fix on 9 usable repositories: within-repository exponent 0.17 to 0.36; R-squared 0.50 to 0.70.

## Pilot 2 (20 repositories, quarterly windows, 2021Q1 to 2026Q2)

Data: `data/pilot_v2/`

| Check | Pilot 1 | Pilot 2 |
| --- | --- | --- |
| Included windows | 104 / 211 | 231 / 432 |
| Repositories with at least 8 usable windows | 10 | 12 |
| Size exponent, pooled | 0.41 | 0.79 (R-squared 0.70) |
| Size exponent, within repository | 0.19 | 0.37 |
| Driver collinearity (VIF) | not checkable | 1.1 to 1.4 |
| AI score before / after adoption | weak | 0.00 / 0.49 (AI group) |

Remaining issues and decisions for the full run:

1. **Continuous driver scores in the main model.** Too many windows are at the extremes (AIAD = 0 in over 80%; DVOP at 0.75 or more in 80%). COCOMO levels are used only when reporting multipliers.
2. **Two comparison repositories per AI repository.** 6 of 10 comparison repositories showed an AI signal during the period.
3. **Contributor screen.** Some active repositories had only 1 or 2 regular developers (rallly: 2,494 commits, no usable windows). Require at least 20 contributors.
4. **Random repository effects.** MSVC barely varies within repositories (within-repository SD 0.025), so its effect is identified between repositories; repository fixed effects would absorb it.

## Hand check (2026Q1 window)

Checked against the repository contents at each window's end commit.

| Repository | Result |
| --- | --- |
| mlflow/mlflow | All match: 56 CI workflow files; pytest in 11 workflows; `.claude/` config; 912 of 1,628 commits AI-authored or co-authored (notebook: 57%); no Dependabot/Renovate; SECURITY.md. Problem: the 3 "service" Dockerfiles are packaging/dev images (`dev/`, `docker/`, `mlflow/R/`) |
| zeromicro/go-zero | All match: 6 CI files; tests; CodeQL; Dependabot; Copilot instructions; SECURITY.md; 28 human and 12 bot (Dependabot) commits. Problem: 3 IaC files and 1 Kubernetes workload are example manifests in `core/discov/kubernetes/` |
| tinygo-org/tinygo | All match: 8 CI files (7 GitHub Actions + CircleCI); tests; Docker push step; no bots, AI or security files. Commit count matches when commits are dated by author date (76 of the 90 Q1 commits were merged in April) |

Decision: commits are dated by **author date** (when the work was done), not by when they were merged. State this in the paper.

## Detection fixes after the hand check

| Rule | New definition | Effect |
| --- | --- | --- |
| Service | Folder with both a Dockerfile and its own build file (package.json, go.mod, pyproject.toml, pom.xml, Cargo.toml, *.csproj, ...), excluding dev, docker, ci, scripts, tools, test, example and docs folders; or a uniquely named Kubernetes workload in a deployment folder; or a docker-compose service built from source. The highest count is used | mlflow 3 to 1; go-zero unchanged at 1; microservices-demo 12 to 15 |
| IaC file | Deployment file in a top-level folder whose name contains deploy, k8s, kube, helm, chart, kustomiz, infra, terraform, manifest, istio, argocd, cloudformation, pulumi, ansible or gitops; or a Terraform, Bicep, Pulumi, CDK, Serverless, Chart.yaml or kustomization file outside test, example and docs folders | go-zero 3 to 0; microservices-demo 32 to 90 (Helm, Kustomize and manifest folders now found) |
| Kubernetes workloads | Counted by unique workload name, so a service defined in Helm, Kustomize and plain manifests counts once | microservices-demo 40 to 15 |

## Effort threshold (Robles et al., 2022)

Robles et al. use a 6-month window and set the threshold per project from developer surveys: OpenStack 12, Moodle 14, Linux 17, WebKit 16 to 19, Ceph 24, MediaWiki 36 to 37 commits per 6 months. A developer at or above the threshold counts as full-time; below it, commits / threshold x period length.

Decision for the full run: main analysis threshold 12 per 6 months (6 per quarter); robustness checks with 17 and 24, 6-month windows, and an "active days" variant. The pilots used a placeholder of 10 commits per month, which underestimates effort.
