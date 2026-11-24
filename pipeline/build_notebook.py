import json, os
H = os.path.dirname(os.path.abspath(__file__))
src = lambda f: open(os.path.join(H, f)).read()

cells = []
def md(t): cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n")})
def code(t): cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                           "outputs": [], "source": t.strip("\n")})

md("""
# COCOMO-Extended — Pilot data-collection notebook (version 2)

**Changes from version 1, based on the first pilot:** quarterly windows; bulk commits (over 2,000 source lines) left out of size; DevOps maturity measured from git (CI workflows, test steps, releases) because GitHub keeps CI-run history for only about a year; an activity screen so inactive repositories are not chosen; AI repositories must have adopted agents by September 2025; AI adoption defined by any AI signal; results saved to a new folder (`pilot_v2`).

This notebook builds the pilot dataset for the paper: **20 public GitHub repositories** (10 that use AI coding agents, 10 matched repositories that do not), measured in **6-month windows from 2021 to mid-2026**.

For every repository-window it computes **effort** (full-time-equivalent developer-months), **size** (KSLOC added/modified) and the **six drivers** (DVOP, AIAD, MSVC, CLAU, MTEX, SECU), each as a 0–1 score and as a COCOMO level (VL = −2 … XH = 3).

**How to run**
1. Create a GitHub token: GitHub → Settings → Developer settings → Personal access tokens → *Fine-grained token*, read-only access to public repositories is enough.
2. In Colab, click the key icon (Secrets) on the left, add a secret named `GITHUB_TOKEN` with the token, and switch on notebook access. (Or paste it when asked.)
3. Run the cells from top to bottom (*Runtime → Run all*). The pilot takes roughly 1–3 hours.
4. Results are saved to Google Drive in `MyDrive/cocomo_extended/pilot/`. If Colab disconnects, run everything again: finished repositories are skipped automatically.

Everything is downloaded automatically: the AIDev dataset from Hugging Face, repository histories with `git clone`, pull-request, release and CI counts from the GitHub API, and security scores from the OpenSSF Scorecard API.
""")

md("## 1. Setup")
code("""
!pip -q install huggingface_hub pyarrow fsspec statsmodels
# Save results to Google Drive if possible; otherwise to the Colab disk (download them at the end).
USE_DRIVE = True
SAVE_ROOT = "/content/cocomo_extended"
if USE_DRIVE:
    try:
        from google.colab import drive
        drive.mount('/content/drive')
        SAVE_ROOT = "/content/drive/MyDrive/cocomo_extended"
    except Exception as e:
        print("Google Drive could not be mounted:", e)
        print("Continuing WITHOUT Drive. Results go to /content/cocomo_extended and are lost when the "
              "session ends - run the download cell at the end. To retry Drive, run this cell again "
              "and tick 'Select all' on the permissions screen.")
print("Results folder:", SAVE_ROOT)
""")
code("""
# GitHub token: read from Colab Secrets, or ask for it
try:
    from google.colab import userdata
    GITHUB_TOKEN = userdata.get('GITHUB_TOKEN')
except Exception:
    from getpass import getpass
    GITHUB_TOKEN = getpass('Paste your GitHub token: ')
print('Token loaded:', bool(GITHUB_TOKEN))
""")

md("""
## 2. Settings
Change values here only. Every cut-off used to turn indicators into scores is listed in `FULL_SCORE_AT` and `LEVEL_CUTS`; **fix them before the full run and record them in the OSF pre-registration**.

`FT_COMMITS_PER_MONTH` is the commit threshold above which a developer counts as one full-time developer in that month (Robles et al., EMSE 2022). Set it from that paper; 10 is a placeholder to check.
""")
code("""
CFG = dict(
    # study period and windows
    START="2021-01-01", END="2026-07-01", WINDOW_MONTHS=3,   # quarterly: more periods after AI adoption
    # effort model (Robles et al. 2022) - CHECK THIS VALUE AGAINST THE PAPER
    FT_COMMITS_PER_MONTH=10,
    # inclusion rules
    CORE_DEV_COMMITS=5, MIN_CORE_DEVS=3, MIN_STARS=100, MIN_KSLOC=1.0,
    BULK_COMMIT_LINES=2000,    # commits adding more source lines than this are left out of size
    LANGS=["Python", "JavaScript", "TypeScript", "Java", "Go", "C#", "Rust"],
    CREATED_BEFORE="2022-01-01", ACTIVE_AFTER="2026-05-01", MAX_REPO_MB=1500,
    ACTIVE_SINCE="2025-01-01", MIN_RECENT_COMMITS=300,   # activity screen before cloning
    # pilot sample
    N_AI=10, MIN_AGENT_PRS=5, ADOPTED_BY="2025-09-30",   # leaves >= 3 quarters after adoption
    MAX_CANDIDATES_CHECKED=300, SEED=42,
    # value at which each indicator counts as fully 'on' (score = 1)
    FULL_SCORE_AT=dict(n_ci_workflows=5, ci_runs_per_week=20, releases_per_month=2, agent_pr_share=0.30,
                       ai_commit_share=0.30, n_services=50, iac_change_share=0.10,
                       tenure_months=72),
    # score -> COCOMO level: <0.10 VL, <0.30 L, <0.50 N, <0.70 H, <0.90 VH, else XH
    LEVEL_CUTS=[0.10, 0.30, 0.50, 0.70, 0.90],
    # where files go
    OUT_DIR=SAVE_ROOT + "/pilot_v2",   # new folder, so version-1 results are not reused
    CLONE_DIR="/content/clones",
    AIDEV_VERSION="v5",
)
import os
os.makedirs(CFG["OUT_DIR"] + "/repos", exist_ok=True)
os.makedirs(CFG["CLONE_DIR"], exist_ok=True)
""")

md("## 3. Measurement functions\nThese read a local git clone. Nothing to change here.")
code(src("core.py"))
md("## 4. API helpers (GitHub, Scorecard, AIDev)")
code(src("api.py"))
code("""
rl = gh_get('/rate_limit')
print('GitHub API OK, requests left this hour:', rl['resources']['core']['remaining'] if rl else 'TOKEN PROBLEM')
""")
md("## 5. Per-repository processing")
code(src("run.py"))

md("## 6. Load AIDev\nDownloads the pull-request table from Hugging Face (a few minutes the first time).")
code("""
aidev_prs, aidev_repos = load_aidev(CFG["AIDEV_VERSION"])
AIDEV_CUTOFF = aidev_prs["created_at"].max()
print(f"{len(aidev_prs):,} agent PRs in {aidev_prs['repo'].nunique():,} repositories; "
      f"data end: {AIDEV_CUTOFF:%Y-%m-%d}")
print("Agents:", aidev_prs["agent"].value_counts().to_dict())
if aidev_repos is not None:
    print("Repository table columns:", list(aidev_repos.columns))
""")

md("""
## 7. Choose the pilot repositories
Picks 10 AI-agent repositories from AIDev and one matched comparison repository for each (same language, similar stars, no AIDev activity). The list is saved, so it is chosen only once.

To use your own list instead, set `MANUAL` to a list of `(repo, group)` pairs, e.g. `[("owner/name", "ai"), ("owner/other", "control")]`.
""")
code(src("select.py"))
code("""
MANUAL = None
pilot_csv = CFG["OUT_DIR"] + "/pilot_repos.csv"
if MANUAL:
    pilot = pd.DataFrame(MANUAL, columns=["repo", "group"])
elif os.path.exists(pilot_csv):
    pilot = pd.read_csv(pilot_csv)
    print("Using saved pilot list")
else:
    ai = select_ai_repos(aidev_prs, aidev_repos, CFG, CFG["N_AI"])
    ctrl = select_control_repos(ai, aidev_prs["repo"].dropna().unique(), CFG)
    pilot = pd.DataFrame(ai + ctrl).rename(columns={"full_name": "repo"})
    pilot.to_csv(pilot_csv, index=False)
display(pilot[[c for c in ["repo", "group", "language", "stars", "created_at", "matched_to",
                           "n_agent_prs"] if c in pilot.columns]])
""")

md("## 8. Run the pipeline\nEach repository is cloned, measured, saved to Drive, and deleted from local disk.")
code("""
failures = []
for i, row in pilot.reset_index(drop=True).iterrows():
    print(f"[{i+1}/{len(pilot)}] {row['repo']} ({row['group']})")
    try:
        process_repo(row["repo"], row["group"], CFG, aidev_prs, AIDEV_CUTOFF)
    except Exception as e:
        print("  FAILED:", str(e)[:300])
        failures.append((row["repo"], str(e)[:300]))
print("Failures:", failures or "none")
""")

md("## 9. Combine and summarise")
code("""
import glob
data = pd.concat([pd.read_csv(f) for f in glob.glob(CFG["OUT_DIR"] + "/repos/*.csv")], ignore_index=True)
# AI adoption = first window with ANY AI signal (agent PRs, AI co-authored commits, AI config file);
# comparison repositories that start using AI become 'adopters' too (handled by the staggered design)
sig = (data["agent_merged_prs"].fillna(0) > 0) | (data["ai_commit_share"].fillna(0) > 0) | (data["has_ai_config"] == 1)
first = data[sig].groupby("repo")["window_start"].min()
data["ai_adopt_start"] = data["repo"].map(first)
data["post_ai"] = (data["ai_adopt_start"].notna() & (data["window_start"] >= data["ai_adopt_start"])).astype(int)
data.to_csv(CFG["OUT_DIR"] + "/pilot_dataset.csv", index=False)
print("Repositories with an AI signal:", first.size, "| control repositories that adopted AI:",
      data[(data["group"] == "control") & data["ai_adopt_start"].notna()]["repo"].nunique())
print(f"{data['repo'].nunique()} repositories, {len(data)} windows, {int(data['include'].sum())} meet the inclusion rules")
drivers = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
display(data[data["include"] == 1][["effort_pm", "ksloc", "team_size"] + drivers].describe().round(2))
display(data.groupby("group")[["effort_pm", "ksloc"] + drivers].mean().round(2))
inc = data[data["include"] == 1]
print("Share of included windows at each level (VL=-2 ... XH=3):")
display(pd.concat({c: inc[f"{c}_level"].value_counts(normalize=True).sort_index() for c in drivers}, axis=1).round(2))
print("Data-based cut-offs (20/40/60/80/95th percentiles of each score) - candidates for LEVEL_CUTS in the pre-registration:")
display(inc[drivers].quantile([0.2, 0.4, 0.6, 0.8, 0.95]).round(3))
""")

md("""
## 10. Check the measures by hand
Pick a repository and window, open the links, and compare with the numbers. Record any mismatch and fix the rule in Section 3 **before** the full run.

What to check: (1) CI files exist and match `has_ci`; (2) the number of services matches the docker-compose / Kubernetes files; (3) IaC files match `n_iac_files`; (4) bots are not counted as human developers; (5) AI config files and AI co-authored commits are real; (6) SECURITY.md, Dependabot/Renovate, CODEOWNERS and SAST in CI match.
""")
code("""
CHECK_REPO = pilot["repo"].iloc[0]          # change to any pilot repository
CHECK_WINDOW = None                          # e.g. "2025H1"; None = latest window
d = data[data["repo"] == CHECK_REPO].sort_values("window")
r = d.iloc[-1] if CHECK_WINDOW is None else d[d["window"] == CHECK_WINDOW].iloc[0]
a = pd.Timestamp(r["window_start"]); b = a + pd.DateOffset(months=CFG["WINDOW_MONTHS"])
base = f"https://github.com/{CHECK_REPO}"
print("Files at window end:  ", f"{base}/tree/{r['end_commit']}")
print("CI workflows:         ", f"{base}/tree/{r['end_commit']}/.github/workflows")
print("Commits in window:    ", f"{base}/commits?since={a:%Y-%m-%d}&until={(b - pd.Timedelta(days=1)):%Y-%m-%d}")
print("Merged PRs in window: ", f"{base}/pulls?q=is%3Apr+is%3Amerged+merged%3A{a:%Y-%m-%d}..{(b - pd.Timedelta(days=1)):%Y-%m-%d}")
cols = ["window", "commits_human", "commits_bot", "commits_ai_author", "team_size", "core_devs",
        "effort_pm", "ksloc", "ksloc_bulk_excluded", "n_bulk_commits", "has_ci", "has_test_in_ci", "n_ci_workflows", "releases_per_month", "agent_pr_share",
        "ai_commit_share", "has_ai_config", "n_services", "svc_compose_built", "svc_k8s_workloads",
        "svc_dockerfile_dirs", "n_iac_files", "ci_deploy", "tenure_months", "has_security_policy",
        "has_dep_update", "has_sast", "has_codeowners"] + drivers
display(r[cols].to_frame().T)
""")

md("""
## 11. Preview analysis (pilot only)
A quick check that the data behave sensibly: driver correlations, multicollinearity, and a simple COCOMO-style regression. **Do not report these numbers in the paper**: the pilot is too small, and the real analysis is the Bayesian model on the full sample.
""")
code("""
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor
d = data[(data["include"] == 1) & (data["effort_pm"] > 0) & (data["ksloc"] > 0)].copy()
d["ln_pm"], d["ln_ksloc"] = np.log(d["effort_pm"]), np.log(d["ksloc"])
print("Driver correlations:"); display(d[drivers].corr().round(2))
X = d[drivers].dropna()
X = X.loc[:, X.std() > 0]
if len(X) > len(X.columns) + 2:
    Xc = np.column_stack([np.ones(len(X)), X.values])
    print("VIF:", {c: round(variance_inflation_factor(Xc, i + 1), 2) for i, c in enumerate(X.columns)})
levels = [f"{c}_level" for c in X.columns]
try:
    if len(d) < 30:
        raise ValueError(f"only {len(d)} included windows; need at least 30 for a meaningful preview")
    m = smf.ols("ln_pm ~ ln_ksloc + " + " + ".join(levels), data=d).fit(
        cov_type="cluster", cov_kwds={"groups": d["repo"]})
    print(m.summary().tables[1])
    print("Size exponent B (preview):", round(m.params["ln_ksloc"], 3), "- plausible range is about 0.9 to 1.2")
except Exception as e:
    print("Regression not possible yet:", e)
sc_cols = [c for c in d.columns if c.startswith("sc_")]
if sc_cols:
    d["scorecard_mean"] = d[sc_cols].mean(axis=1) / 10
    print("SECU vs current OpenSSF Scorecard, correlation:",
          round(d[["SECU", "scorecard_mean"]].corr().iloc[0, 1], 2))
""")

md("## 12. Download the results (needed if you are not using Google Drive)")
code("""
import shutil
from google.colab import files
zip_path = shutil.make_archive("/content/cocomo_pilot_results", "zip", CFG["OUT_DIR"])
files.download(zip_path)
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                    "language_info": {"name": "python"}, "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}
# source must be list of lines for best compatibility
for c in nb["cells"]:
    c["source"] = [l + "\n" for l in c["source"].split("\n")]
    c["source"][-1] = c["source"][-1].rstrip("\n")
json.dump(nb, open(os.path.join(H, "..", "notebooks", "COCOMO_Extended_pilot.ipynb"), "w"), indent=1)
print("written", len(cells), "cells")
