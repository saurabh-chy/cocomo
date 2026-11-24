# ===================== GITHUB / SCORECARD / AIDEV HELPERS =====================
import time, random, requests

SESSION = requests.Session()

def gh_get(url, params=None, search=False):
    """GET from the GitHub API with automatic waiting on rate limits."""
    if not url.startswith("http"):
        url = "https://api.github.com" + url
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    for attempt in range(6):
        if search:
            time.sleep(2.2)              # search API: 30 requests per minute
        r = SESSION.get(url, headers=headers, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (403, 429) and (r.headers.get("X-RateLimit-Remaining") == "0"
                                            or "rate limit" in r.text.lower()):
            reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(5, reset - time.time() + 5)
            print(f"  rate limit reached, waiting {wait/60:.1f} min")
            time.sleep(wait)
            continue
        if r.status_code in (502, 503, 504):
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code in (404, 409, 410, 422, 451):
            return None
        time.sleep(5)
    return None

def commit_count_since(full_name, since):
    """Number of commits on the default branch since a date (one API call, via the Link header)."""
    url = f"https://api.github.com/repos/{full_name}/commits"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    try:
        r = SESSION.get(url, headers=headers, params={"since": since, "per_page": 1}, timeout=60)
        if r.status_code != 200:
            return 0
        m = re.search(r'[?&]page=(\d+)>; rel="last"', r.headers.get("Link", ""))
        return int(m.group(1)) if m else len(r.json())
    except Exception:
        return 0

def repo_meta(full_name):
    j = gh_get(f"/repos/{full_name}")
    if not j:
        return None
    return {"full_name": j["full_name"], "stars": j["stargazers_count"], "language": j["language"],
            "created_at": j["created_at"], "fork": j["fork"], "archived": j["archived"],
            "size_mb": j["size"] / 1024, "owner_type": j["owner"]["type"],
            "default_branch": j["default_branch"]}

def merged_pr_count(full_name, a, b):
    q = f"repo:{full_name} is:pr is:merged merged:{a:%Y-%m-%d}..{(b - pd.Timedelta(days=1)):%Y-%m-%d}"
    j = gh_get("/search/issues", params={"q": q, "per_page": 1}, search=True)
    return j["total_count"] if j else np.nan

def ci_run_count(full_name, a, b):
    j = gh_get(f"/repos/{full_name}/actions/runs",
               params={"created": f"{a:%Y-%m-%d}..{(b - pd.Timedelta(days=1)):%Y-%m-%d}", "per_page": 1})
    return j.get("total_count", np.nan) if j else np.nan

SCORECARD_CHECKS = ["Branch-Protection", "Code-Review", "SAST", "Dependency-Update-Tool", "Security-Policy"]

def scorecard(full_name):
    """Current OpenSSF Scorecard check scores (0-10); NaN if not available."""
    try:
        r = SESSION.get(f"https://api.securityscorecards.dev/projects/github.com/{full_name}", timeout=60)
        if r.status_code != 200:
            return {}
        checks = {c["name"]: c.get("score", -1) for c in r.json().get("checks", [])}
        return {f"sc_{k}": (checks[k] if checks.get(k, -1) >= 0 else np.nan) for k in SCORECARD_CHECKS}
    except Exception:
        return {}

# ---------- AIDev ----------
def load_aidev(version="v5"):
    base = f"hf://datasets/hao-li/AIDev@{version}"
    prs = pd.read_parquet(f"{base}/all_pull_request.parquet",
                          columns=["repo_url", "agent", "created_at", "merged_at"])
    prs["repo"] = prs["repo_url"].str.extract(r"github\.com/(?:repos/)?([^/]+/[^/]+?)(?:\.git)?/?$")[0]
    prs["created_at"] = pd.to_datetime(prs["created_at"], utc=True, errors="coerce")
    prs["merged_at"] = pd.to_datetime(prs["merged_at"], utc=True, errors="coerce")
    try:
        repos = pd.read_parquet(f"{base}/all_repository.parquet")
    except Exception as e:
        print("Could not load all_repository:", e)
        repos = None
    return prs, repos

def detect_col(df, *keys):
    for k in keys:
        for c in df.columns:
            if k in c.lower():
                return c
    return None
