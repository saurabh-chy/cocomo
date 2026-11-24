"""Builds notebooks/COCOMO_Extended_full_run.ipynb from the pipeline modules.
Run:  python pipeline/build_notebook.py
(The pilot notebook in notebooks/ is kept as a record and is no longer rebuilt.)"""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
src = lambda f: open(os.path.join(H, f)).read()

cells = []
def md(t): cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n")})
def code(t): cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                           "outputs": [], "source": t.strip("\n")})

md("""
# COCOMO-Extended — Full data-collection run

Builds the study dataset: about **200 repositories that use AI coding agents and 400 matched comparison repositories** (2 per AI repository), measured in **quarterly windows from 2021 Q1 to 2026 Q2**.

For every repository-window it records effort (full-time-equivalent developer-months, Robles et al. 2022), size (KSLOC added, bulk commits excluded) and the six drivers (DVOP, AIAD, MSVC, CLAU, MTEX, SECU) as continuous 0–1 scores, plus robustness variants of effort.

**This takes several Colab sessions.** Each session processes repositories until its time budget runs out, saving each one as it finishes. Just run the notebook again (Runtime → Run all) and it continues where it stopped. Keep the browser tab open while it runs: Colab disconnects idle sessions.

**Use Google Drive.** Without Drive, results are lost when a session ends unless you download them (section 10) and upload them again at the start of the next session (section 1b).

Before starting: add the GitHub token as a Colab secret named `GITHUB_TOKEN` (key icon on the left, notebook access on).
""")

md("## 1. Setup")
code("""
!pip -q install huggingface_hub pyarrow fsspec statsmodels
USE_DRIVE = True
SAVE_ROOT = "/content/cocomo_extended"
if USE_DRIVE:
    try:
        from google.colab import drive
        drive.mount('/content/drive')
        SAVE_ROOT = "/content/drive/MyDrive/cocomo_extended"
    except Exception as e:
        print("Google Drive could not be mounted:", e)
        print("Continuing WITHOUT Drive: download the results at the end of every session (section 10).")
print("Results folder:", SAVE_ROOT)
""")
md("### 1b. Only without Google Drive: restore earlier results\nIf you downloaded a results zip in an earlier session, set `RESTORE = True`, run this cell and choose the zip. Skip it otherwise.")
code("""
RESTORE = False
if RESTORE:
    import zipfile, io, os
    from google.colab import files
    up = files.upload()
    for name, data in up.items():
        os.makedirs(SAVE_ROOT + "/full_run", exist_ok=True)
        zipfile.ZipFile(io.BytesIO(data)).extractall(SAVE_ROOT + "/full_run")
        print("Restored", name)
""")
code("""
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
These values are the study's pre-registered rules. **Do not change them after the full run has started**, or the repositories already processed will have been measured differently.

* Effort: a developer with at least `THETA_6M` commits per 6 months counts as full-time; others count in proportion (Robles et al. 2022; 12 = OpenStack). The threshold is scaled to the window length. `THETA_ROBUST` and the active-days and 6-month versions are robustness checks.
* Drivers are kept as continuous 0–1 scores for the main model. `LEVEL_CUTS` only converts them to COCOMO levels for reporting.
""")
code("""
CFG = dict(
    START="2021-01-01", END="2026-07-01", WINDOW_MONTHS=3,
    # effort (Robles et al. 2022)
    THETA_6M=12, THETA_ROBUST=[17, 24],
    # inclusion rules for a window
    CORE_DEV_COMMITS=5, MIN_CORE_DEVS=3, MIN_KSLOC=1.0, BULK_COMMIT_LINES=2000,
    # repository screen
    MIN_STARS=100, LANGS=["Python", "JavaScript", "TypeScript", "Java", "Go", "C#", "Rust"],
    CREATED_BEFORE="2022-01-01", ACTIVE_AFTER="2026-05-01", MAX_REPO_MB=1500,
    ACTIVE_SINCE="2025-01-01", MIN_RECENT_COMMITS=300, MIN_CONTRIBUTORS=20,
    # sample
    N_AI=200, CONTROLS_PER_AI=2, MIN_AGENT_PRS=5, ADOPTED_BY="2025-09-30",
    MAX_CANDIDATES_CHECKED=3000, SEED=42,
    # value at which each indicator counts as fully 'on' (score = 1)
    FULL_SCORE_AT=dict(n_ci_workflows=5, ci_runs_per_week=20, releases_per_month=2, agent_pr_share=0.30,
                       ai_commit_share=0.30, n_services=50, iac_change_share=0.10, tenure_months=72),
    # reporting only: score -> COCOMO level (<0.10 VL, <0.30 L, <0.50 N, <0.70 H, <0.90 VH, else XH)
    LEVEL_CUTS=[0.10, 0.30, 0.50, 0.70, 0.90],
    # session control
    MAX_HOURS_PER_SESSION=10,
    OUT_DIR=SAVE_ROOT + "/full_run", CLONE_DIR="/content/clones", AIDEV_VERSION="v5",
)
import os, json
os.makedirs(CFG["OUT_DIR"] + "/repos", exist_ok=True)
os.makedirs(CFG["CLONE_DIR"], exist_ok=True)
# record the settings used, and refuse to continue with different ones
cfg_file = CFG["OUT_DIR"] + "/settings.json"
saved = json.load(open(cfg_file)) if os.path.exists(cfg_file) else None
current = {k: v for k, v in CFG.items() if k not in ("OUT_DIR", "CLONE_DIR", "MAX_HOURS_PER_SESSION")}
if saved is None:
    json.dump(current, open(cfg_file, "w"), indent=1)
    print("Settings saved.")
elif saved != current:
    raise SystemExit("Settings differ from the ones this run started with: " +
                     str({k: (saved.get(k), current.get(k)) for k in current if saved.get(k) != current.get(k)}))
else:
    print("Settings match the saved run.")
""")

md("## 3. Measurement functions")
code(src("core.py"))
md("## 4. API helpers")
code(src("api.py"))
code("""
rl = gh_get('/rate_limit')
print('GitHub API OK, requests left this hour:', rl['resources']['core']['remaining'] if rl else 'TOKEN PROBLEM')
""")
md("## 5. Per-repository processing")
code(src("run.py"))

md("## 6. Load AIDev")
code("""
aidev_prs, aidev_repos = load_aidev(CFG["AIDEV_VERSION"])
AIDEV_CUTOFF = aidev_prs["created_at"].max()
print(f"{len(aidev_prs):,} agent PRs in {aidev_prs['repo'].nunique():,} repositories; data end: {AIDEV_CUTOFF:%Y-%m-%d}")
""")

md("""
## 7. Choose the sample (first session only)
Selects the AI repositories and 2 comparison repositories for each, then saves the list. This takes 1–3 hours the first time; later sessions reuse the saved list.
""")
code(src("select.py"))
code("""
sample_csv = CFG["OUT_DIR"] + "/sample.csv"
if os.path.exists(sample_csv):
    sample = pd.read_csv(sample_csv)
    print("Using saved sample")
else:
    ai = select_ai_repos(aidev_prs, aidev_repos, CFG, CFG["N_AI"])
    pd.DataFrame(ai).to_csv(CFG["OUT_DIR"] + "/sample_ai_only.csv", index=False)   # in case the next step is interrupted
    ctrl = select_control_repos(ai, aidev_prs["repo"].dropna().unique(), CFG)
    sample = pd.DataFrame(ai + ctrl).rename(columns={"full_name": "repo"})
    sample.to_csv(sample_csv, index=False)
print(sample["group"].value_counts().to_dict())
display(sample.groupby(["group", "language"]).size().unstack(0).fillna(0).astype(int))
""")

md("## 8. Run (resumable)\nProcesses repositories not yet done, until `MAX_HOURS_PER_SESSION` is reached. Rerun the notebook to continue.")
code("""
import time
done = {f[:-4].replace("__", "/") for f in os.listdir(CFG["OUT_DIR"] + "/repos") if f.endswith(".csv")}
fail_csv = CFG["OUT_DIR"] + "/failures.csv"
todo = [r for r in sample.itertuples() if r.repo not in done]
print(f"Done: {len(done)} | to do: {len(todo)}")
t0 = time.time()
for i, row in enumerate(todo):
    if (time.time() - t0) / 3600 > CFG["MAX_HOURS_PER_SESSION"]:
        print("Session time budget reached. Download the results if not using Drive, then rerun to continue.")
        break
    print(f"[{len(done) + i + 1}/{len(sample)}] {row.repo} ({row.group})")
    try:
        process_repo(row.repo, row.group, CFG, aidev_prs, AIDEV_CUTOFF)
    except Exception as e:
        print("  FAILED:", str(e)[:300])
        pd.DataFrame([{"repo": row.repo, "error": str(e)[:300], "time": pd.Timestamp.now()}]).to_csv(
            fail_csv, mode="a", header=not os.path.exists(fail_csv), index=False)
left = len([r for r in sample.repo if not os.path.exists(CFG["OUT_DIR"] + "/repos/" + r.replace("/", "__") + ".csv")])
print("Repositories still to do:", left)
""")

md("## 9. Combine (run when everything is done, or at any time for a progress check)")
code("""
import glob
files_ = glob.glob(CFG["OUT_DIR"] + "/repos/*.csv")
data = pd.concat([pd.read_csv(f) for f in files_], ignore_index=True)
sig = (data["agent_merged_prs"].fillna(0) > 0) | (data["ai_commit_share"].fillna(0) > 0) | (data["has_ai_config"] == 1)
first = data[sig].groupby("repo")["window_start"].min()
data["ai_adopt_start"] = data["repo"].map(first)
data["post_ai"] = (data["ai_adopt_start"].notna() & (data["window_start"] >= data["ai_adopt_start"])).astype(int)
owner = data["owner_type"] if "owner_type" in data else pd.Series("", index=data.index)
data["company_led"] = ((owner == "Organization") & (data["top_corp_domain_share"] >= 0.5)).astype(int)
data.to_csv(CFG["OUT_DIR"] + "/dataset_quarterly.csv", index=False)
six = pd.concat([pd.read_csv(f) for f in glob.glob(CFG["OUT_DIR"] + "/repos_6m/*.csv")], ignore_index=True)
six.to_csv(CFG["OUT_DIR"] + "/dataset_6month_effort.csv", index=False)
drivers = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
inc = data[data["include"] == 1]
print(f"{data['repo'].nunique()} repositories ({first.size} with an AI signal), {len(data)} windows, {len(inc)} included")
print("Never-adopting repositories:", data.groupby("repo")["ai_adopt_start"].first().isna().sum())
display(inc.groupby("group")[["effort_pm", "ksloc", "team_size"] + drivers].mean().round(2))
if os.path.exists(fail_csv):
    print("Failures so far:"); display(pd.read_csv(fail_csv).tail(20))
""")

md("## 10. Download the results (needed without Google Drive; optional with it)")
code("""
import shutil
from google.colab import files
zip_path = shutil.make_archive("/content/cocomo_full_run_results", "zip", CFG["OUT_DIR"])
files.download(zip_path)
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                    "language_info": {"name": "python"}, "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}
for c in nb["cells"]:
    c["source"] = [l + "\n" for l in c["source"].split("\n")]
    c["source"][-1] = c["source"][-1].rstrip("\n")
out = os.path.join(H, "..", "notebooks", "COCOMO_Extended_full_run.ipynb")
json.dump(nb, open(out, "w"), indent=1)
print("written", len(cells), "cells ->", os.path.normpath(out))
