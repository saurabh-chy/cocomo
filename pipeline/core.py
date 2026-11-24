# ===================== MEASUREMENT FUNCTIONS (git-based) =====================
# Everything in this cell works from a local git clone; no API calls.
import os, re, math, json, shutil, subprocess
from collections import defaultdict
import pandas as pd
import numpy as np
import yaml

# ---------- windows ----------
def make_windows(start, end, months):
    """Return list of (label, start_ts, end_ts) half-open windows [start, end)."""
    edges = pd.date_range(start=start, end=end, freq=f"{months}MS", tz="UTC")
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        if months == 6:
            lab = f"{a.year}H{1 if a.month <= 6 else 2}"
        elif months == 3:
            lab = f"{a.year}Q{(a.month - 1) // 3 + 1}"
        else:
            lab = a.strftime("%Y-%m")
        out.append((lab, a, b))
    return out

# ---------- git helpers ----------
def run(cmd, cwd=None, timeout=3600):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])}... failed: {r.stderr[:300]}")
    return r.stdout

def clone_repo(full_name, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    run(["git", "clone", "--quiet", "--no-checkout", "--single-branch",
         f"https://github.com/{full_name}.git", dest], timeout=5400)

REC, FLD = "\x1e", "\x1f"

def _clean_path(p):
    p = p.strip()
    if "{" in p and "=>" in p:
        p = re.sub(r"\{([^{}]*) => ([^{}]*)\}", r"\2", p)
        p = p.replace("//", "/")
    elif " => " in p:
        p = p.split(" => ")[1]
    return p

def read_commits(repo_dir, since, until):
    """Non-merge commits on the default branch with numstat, between since and until."""
    fmt = f"{REC}%H{FLD}%ae{FLD}%an{FLD}%aI{FLD}%B{FLD}"
    out = run(["git", "log", "--no-merges", "--numstat", f"--format={fmt}",
               f"--since={since}", f"--until={until}"], cwd=repo_dir)
    commits = []
    for rec in out.split(REC)[1:]:
        parts = rec.split(FLD)
        if len(parts) < 6:
            continue
        sha, email, name, date, body, stat = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        files = []
        for line in stat.strip().splitlines():
            cols = line.split("\t")
            if len(cols) != 3:
                continue
            a, d, p = cols
            files.append((int(a) if a.isdigit() else 0, int(d) if d.isdigit() else 0, _clean_path(p)))
        commits.append({"sha": sha, "email": email.lower().strip(), "name": name.strip(),
                        "date": pd.Timestamp(date).tz_convert("UTC"), "body": body, "files": files})
    return commits

def first_commit_dates(repo_dir):
    """First-ever commit date per author email (full history) for team-experience."""
    out = run(["git", "log", "--no-merges", "--format=%ae%x1f%aI", "--reverse"], cwd=repo_dir)
    first = {}
    for line in out.splitlines():
        if FLD not in line:
            continue
        e, d = line.split(FLD)
        e = e.lower().strip()
        if e not in first:
            first[e] = pd.Timestamp(d).tz_convert("UTC")
    return first

def tag_dates(repo_dir):
    out = run(["git", "for-each-ref", "refs/tags", "--format=%(creatordate:iso-strict)"], cwd=repo_dir)
    ds = []
    for line in out.splitlines():
        line = line.strip()
        if line:
            try:
                ds.append(pd.Timestamp(line).tz_convert("UTC"))
            except Exception:
                pass
    return ds

def commit_at(repo_dir, before_ts):
    out = run(["git", "rev-list", "-1", f"--before={before_ts.isoformat()}", "HEAD"], cwd=repo_dir).strip()
    return out or None

def list_files(repo_dir, sha):
    return run(["git", "ls-tree", "-r", "--name-only", sha], cwd=repo_dir).splitlines()

def file_size(repo_dir, sha, path):
    try:
        return int(run(["git", "cat-file", "-s", f"{sha}:{path}"], cwd=repo_dir).strip())
    except Exception:
        return 10**9

def read_file(repo_dir, sha, path, max_bytes=300_000):
    if file_size(repo_dir, sha, path) > max_bytes:
        return ""
    try:
        return run(["git", "show", f"{sha}:{path}"], cwd=repo_dir, timeout=120)
    except Exception:
        return ""

# ---------- classification of authors ----------
BOT_RE = re.compile(r"\[bot\]|(^|[^a-z])bot@|dependabot|renovate|github-actions|pre-commit-ci|codecov|"
                    r"greenkeeper|snyk-bot|allcontributors|semantic-release|mergify|imgbot|"
                    r"weblate|transifex|crowdin|azure-pipelines|travis", re.I)
AI_RE = re.compile(r"copilot|devin-ai|noreply@anthropic\.com|(^|[^a-z])claude($|[^a-z])|"
                   r"chatgpt-codex|openai-codex|codex\[bot\]|cursoragent|cursor\[bot\]|"
                   r"jules\[bot\]|openhands|aider|factory-droid|gemini-code-assist|sweep-ai", re.I)
COAUTHOR_RE = re.compile(r"^co-authored-by:\s*(.+)$", re.I | re.M)

def author_kind(name, email):
    s = f"{name} <{email}>"
    if AI_RE.search(s):
        return "ai"
    if BOT_RE.search(s):
        return "bot"
    return "human"

def has_ai_coauthor(body):
    return any(AI_RE.search(m) for m in COAUTHOR_RE.findall(body or ""))

# ---------- file classification ----------
SRC_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".kt", ".scala", ".go",
           ".cs", ".rs", ".rb", ".php", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".swift",
           ".m", ".vue", ".svelte", ".dart", ".ex", ".exs", ".clj", ".fs", ".lua"}
EXCL_DIR_RE = re.compile(r"(^|/)(vendor|third_party|thirdparty|node_modules|dist|build|out|target|"
                         r"generated|gen|\.yarn|bower_components|site-packages|external)/", re.I)
EXCL_FILE_RE = re.compile(r"(\.min\.js$|_pb2(_grpc)?\.py$|\.pb\.go$|\.pb\.(h|cc)$|\.g\.dart$|"
                          r"\.generated\.|\.designer\.cs$|bundle\.js$)", re.I)
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec|specs|testing|e2e|test_?data|fixtures)/|"
                     r"(^|/)test_[^/]*$|_test\.[a-z]+$|\.(test|spec)\.[a-z]+$|Tests?\.(java|kt|cs)$", re.I)

def file_class(path):
    """'src', 'test' or None (not counted in size)."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in SRC_EXT or EXCL_DIR_RE.search(path) or EXCL_FILE_RE.search(path):
        return None
    return "test" if TEST_RE.search(path) else "src"

CI_RE = re.compile(r"^(\.github/workflows/[^/]+\.ya?ml|\.gitlab-ci\.yml|\.circleci/config\.ya?ml|"
                   r"Jenkinsfile|\.travis\.yml|azure-pipelines\.ya?ml|\.drone\.yml|bitbucket-pipelines\.yml|"
                   r"\.buildkite/.+\.ya?ml)$")
# deployment folders: only at the top level (or one level under deploy-type roots), never inside source code
DEPLOY_ROOT = (r"(ops|tf|cfn|\.?[^/]*(deploy|k8s|kube|helm|chart|kustomiz|infra|terraform|manifest|istio|argocd|"
               r"cloudformation|pulumi|ansible|gitops)[^/]*)")
IAC_RE = re.compile(r"(\.tf$|\.tfvars$|\.bicep$|(^|/)Pulumi\.ya?ml$|(^|/)Chart\.ya?ml$|"
                    r"(^|/)kustomization\.ya?ml$|(^|/)serverless\.ya?ml$|(^|/)cdk\.json$|"
                    r"(^|/)skaffold\.ya?ml$|\.ya?ml$|\.json$)", re.I)
IAC_LOC_RE = re.compile(r"^(" + DEPLOY_ROOT + r"/|[^/]+/" + DEPLOY_ROOT + r"/)", re.I)
IAC_STRONG_RE = re.compile(r"(\.tf$|\.bicep$|(^|/)Pulumi\.ya?ml$|(^|/)cdk\.json$|(^|/)serverless\.ya?ml$|"
                           r"^skaffold\.ya?ml$|^cloudbuild\.ya?ml$|(^|/)Chart\.ya?ml$|(^|/)kustomization\.ya?ml$)", re.I)

def is_iac(path):
    """IaC file in a top-level deployment folder; Terraform/Bicep/Pulumi/CDK/Serverless files anywhere
    outside source, test, example and docs folders."""
    if NONPROD_DIR_RE.search(path):
        return False
    if IAC_STRONG_RE.search(path):
        return True
    return bool(IAC_LOC_RE.search(path)) and path.lower().endswith((".yml", ".yaml", ".json", ".tf", ".tfvars"))

COMPOSE_RE = re.compile(r"(^|/)(docker-)?compose[^/]*\.ya?ml$", re.I)
K8S_DIR_RE = IAC_LOC_RE   # Kubernetes manifests counted only in top-level deployment folders
DOCKERFILE_RE = re.compile(r"(^|/)Dockerfile[^/]*$|\.Dockerfile$", re.I)
NONPROD_DIR_RE = re.compile(r"(^|/)(tests?|testing|testdata|examples?|samples?|docs?|\.devcontainer|benchmarks?|demos?|e2e|"
                            r"fixtures|integration)/", re.I)
PACKAGING_DIR_RE = re.compile(r"(^|/)(dev|docker|ci|scripts?|tools|build|\.github|hack|contrib)(/|$)", re.I)
BUILD_FILE_RE = re.compile(r"(^|/)(package\.json|go\.mod|pyproject\.toml|setup\.py|requirements\.txt|pom\.xml|"
                           r"build\.gradle(\.kts)?|Cargo\.toml|[^/]+\.csproj|Gemfile|composer\.json|mix\.exs)$", re.I)
AI_CFG_RE = re.compile(r"^(\.github/copilot-instructions\.md|\.github/instructions/.+|\.cursorrules|"
                       r"\.cursor/.+|CLAUDE\.md|\.claude/.+|AGENTS\.md|GEMINI\.md|\.aider[^/]*|"
                       r"\.windsurfrules|\.clinerules.*|\.continue/.+)$", re.I)
SECPOL_RE = re.compile(r"^(\.github/|docs/)?SECURITY\.(md|rst|txt)$", re.I)
DEPUPD_RE = re.compile(r"^(\.github/dependabot\.ya?ml|renovate\.json5?|\.renovaterc(\.json)?|"
                       r"\.github/renovate\.json5?)$", re.I)
CODEOWNERS_RE = re.compile(r"^(\.github/|docs/)?CODEOWNERS$")
SAST_RE = re.compile(r"codeql|semgrep|snyk|bandit|gosec|sonar|trivy|grype|brakeman|"
                     r"ossf/scorecard|osv-scanner|zizmor", re.I)
DEPLOY_RE = re.compile(r"terraform\s+(apply|plan)|helm\s+(upgrade|install)|kubectl\s+(apply|rollout|set)|"
                       r"aws\s+(cloudformation|ecs|lambda|s3\s+sync)|gcloud\s+\S*\s*deploy|"
                       r"az\s+(webapp|deployment|containerapp)|serverless\s+deploy|pulumi\s+up|"
                       r"flyctl\s+deploy|vercel|netlify\s+deploy|docker/build-push-action|"
                       r"docker\s+push|environment:\s*(production|prod)\b", re.I)
TEST_STEP_RE = re.compile(r"pytest|tox\b|nox\b|npm\s+(run\s+)?test|yarn\s+(run\s+)?test|pnpm\s+(run\s+)?test|"
                          r"jest|vitest|mocha|go\s+test|cargo\s+(test|nextest)|mvn\s|gradle|dotnet\s+test|"
                          r"make\s+(test|check)|phpunit|rspec|ctest|playwright|cypress", re.I)
K8S_KIND_RE = re.compile(r"^kind:\s*(Deployment|StatefulSet|DaemonSet)\s*$", re.M)

# ---------- scoring ----------
def cap(x, full):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return np.nan
    return float(min(1.0, max(0.0, x / full)))

def mean_avail(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.mean(xs)) if xs else np.nan

def to_level(score, cuts):
    """Map a 0-1 score to COCOMO levels coded VL=-2 ... XH=3."""
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return np.nan
    return -2 + int(np.searchsorted(cuts, score, side="right"))

# ---------- tree-based measures at the end of a window ----------
def tree_measures(repo_dir, sha, max_yaml=300):
    files = list_files(repo_dir, sha)
    m = {}
    ci_files = [f for f in files if CI_RE.search(f)]
    m["has_ci"] = int(bool(ci_files))
    iac_files = [f for f in files if is_iac(f)]
    m["n_iac_files"] = len(iac_files)
    m["has_ai_config"] = int(any(AI_CFG_RE.search(f) for f in files))
    m["has_security_policy"] = int(any(SECPOL_RE.search(f) for f in files))
    m["has_dep_update"] = int(any(DEPUPD_RE.search(f) for f in files))
    m["has_codeowners"] = int(any(CODEOWNERS_RE.search(f) for f in files))

    # CI workflow contents: SAST and deployment steps
    ci_text = "\n".join(read_file(repo_dir, sha, f) for f in ci_files[:60])
    m["has_sast"] = int(bool(SAST_RE.search(ci_text)))
    m["ci_deploy"] = int(bool(DEPLOY_RE.search(ci_text)))
    m["has_test_in_ci"] = int(bool(TEST_STEP_RE.search(ci_text)))
    m["n_ci_workflows"] = len(ci_files)

    # services: docker-compose services with a build key
    compose_built = 0
    for f in [f for f in files if COMPOSE_RE.search(f) and not NONPROD_DIR_RE.search(f)][:20]:
        try:
            doc = yaml.safe_load(read_file(repo_dir, sha, f)) or {}
            svcs = doc.get("services", {}) if isinstance(doc, dict) else {}
            if isinstance(svcs, dict):
                compose_built = max(compose_built, sum(1 for v in svcs.values()
                                                       if isinstance(v, dict) and "build" in v))
        except Exception:
            pass
    # Kubernetes workloads in deployment directories
    # unique workload names, so the same service defined in Helm, Kustomize and plain manifests counts once
    names = set()
    yfiles = [f for f in files if f.lower().endswith((".yml", ".yaml")) and K8S_DIR_RE.search(f)
              and not NONPROD_DIR_RE.search(f)][:max_yaml]
    for f in yfiles:
        for doc in re.split(r"(?m)^---\s*$", read_file(repo_dir, sha, f)):
            if K8S_KIND_RE.search(doc):
                mm = re.search(r"(?m)^metadata:\s*\n(?:[ \t]+.*\n)*?[ \t]+name:\s*['\"]?([^\s'\"]+)", doc)
                nm = mm.group(1) if mm else f
                if "{{" in nm:                      # Helm template name: use the file name instead
                    nm = os.path.splitext(os.path.basename(f))[0]
                names.add(nm.lower())
    k8s = len(names)
    # directories with their own Dockerfile
    # a service = a folder with its own Dockerfile AND its own build file (not a packaging/dev image folder)
    build_dirs = {os.path.dirname(f) for f in files if BUILD_FILE_RE.search(f)}
    dock_dirs = {os.path.dirname(f) for f in files if DOCKERFILE_RE.search(f) and not NONPROD_DIR_RE.search(f)
                 and not PACKAGING_DIR_RE.search(os.path.dirname(f) + "/") and os.path.dirname(f) in build_dirs}
    m["svc_compose_built"], m["svc_k8s_workloads"], m["svc_dockerfile_dirs"] = compose_built, k8s, len(dock_dirs)
    m["n_services"] = max(1, compose_built, k8s, len(dock_dirs))
    m["_iac_set"] = set(iac_files)
    m["_ci_set"] = set(ci_files)
    return m

# ---------- one window ----------
def window_measures(commits, first_dates, tags, w_start, w_end, cfg):
    cw = [c for c in commits if w_start <= c["date"] < w_end]
    for c in cw:
        c["kind"] = author_kind(c["name"], c["email"])
    human = [c for c in cw if c["kind"] == "human"]
    row = {"commits_total": len(cw), "commits_human": len(human),
           "commits_bot": sum(c["kind"] == "bot" for c in cw),
           "commits_ai_author": sum(c["kind"] == "ai" for c in cw)}

    # effort: full-time-equivalent developer-months (Robles et al.)
    per_dev_month = defaultdict(int)
    for c in human:
        per_dev_month[(c["email"], c["date"].strftime("%Y-%m"))] += 1
    T = cfg["FT_COMMITS_PER_MONTH"]
    row["effort_pm"] = float(sum(min(1.0, n / T) for n in per_dev_month.values()))

    dev_commits = defaultdict(int)
    for c in human:
        dev_commits[c["email"]] += 1
    row["team_size"] = len(dev_commits)
    row["core_devs"] = sum(1 for n in dev_commits.values() if n >= cfg["CORE_DEV_COMMITS"])

    # size: source lines added (added + modified lines appear as added in numstat)
    # bulk commits (imports, generated or vendored code) are left out of size
    src = test = bulk = nbulk = 0
    for c in human:
        cs = sum(a for a, d, p in c["files"] if file_class(p) == "src")
        if cs > cfg["BULK_COMMIT_LINES"]:
            bulk += cs
            nbulk += 1
            continue
        src += cs
        test += sum(a for a, d, p in c["files"] if file_class(p) == "test")
    row["ksloc"] = src / 1000.0
    row["ksloc_test"] = test / 1000.0
    row["ksloc_bulk_excluded"] = bulk / 1000.0
    row["n_bulk_commits"] = nbulk

    # AI commits (authored by agents or with an AI co-author trailer)
    nonbot = [c for c in cw if c["kind"] != "bot"]
    ai_commits = sum(1 for c in nonbot if c["kind"] == "ai" or has_ai_coauthor(c["body"]))
    row["ai_commit_share"] = ai_commits / len(nonbot) if nonbot else np.nan

    # releases
    months = (w_end - w_start).days / 30.44
    row["releases_per_month"] = sum(w_start <= t < w_end for t in tags) / months

    # team experience: commit-weighted mean months since each developer's first commit
    tenures, weights = [], []
    for e, n in dev_commits.items():
        fd = first_dates.get(e)
        if fd is not None:
            tenures.append(max(0.0, (w_start - fd).days / 30.44))
            weights.append(n)
    row["tenure_months"] = float(np.average(tenures, weights=weights)) if tenures else np.nan

    # company-led signal: share of human commits from the most common corporate email domain
    PUBLIC = {"gmail.com", "users.noreply.github.com", "outlook.com", "hotmail.com", "yahoo.com",
              "qq.com", "163.com", "protonmail.com", "proton.me", "icloud.com", "me.com", "live.com",
              "googlemail.com", "gmx.de", "web.de", "mail.ru", "yandex.ru", "126.com", "foxmail.com"}
    doms = defaultdict(int)
    for c in human:
        d = c["email"].split("@")[-1]
        if d and d not in PUBLIC and "." in d:
            doms[d] += 1
    top = max(doms.items(), key=lambda kv: kv[1]) if doms else (None, 0)
    row["top_corp_domain"] = top[0]
    row["top_corp_domain_share"] = top[1] / len(human) if human else np.nan
    row["_human_commits"] = human
    return row
