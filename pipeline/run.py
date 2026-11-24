# ===================== PROCESS ONE REPOSITORY =====================
def process_repo(full_name, group, cfg, aidev_prs, aidev_cutoff, use_api=True):
    out_csv = os.path.join(cfg["OUT_DIR"], "repos", full_name.replace("/", "__") + ".csv")
    if os.path.exists(out_csv):
        print(f"  already done: {full_name}")
        return pd.read_csv(out_csv)
    meta = repo_meta(full_name) if use_api else {}
    sc = scorecard(full_name) if use_api else {}
    tmp = os.path.join(cfg["CLONE_DIR"], full_name.replace("/", "__"))
    t0 = time.time()
    clone_repo(full_name, tmp)
    try:
        windows = make_windows(cfg["START"], cfg["END"], cfg["WINDOW_MONTHS"])
        commits = read_commits(tmp, cfg["START"], cfg["END"])
        firsts = first_commit_dates(tmp)
        tags = tag_dates(tmp)
        agent = aidev_prs[(aidev_prs["repo"] == full_name) & aidev_prs["merged_at"].notna()] \
            if aidev_prs is not None else None
        rows = []
        for label, a, b in windows:
            sha = commit_at(tmp, b)
            if sha is None:
                continue
            r = {"repo": full_name, "group": group, "window": label,
                 "window_start": a.date().isoformat(), "end_commit": sha}
            r.update(window_measures(commits, firsts, tags, a, b, cfg))
            human = r.pop("_human_commits")
            if r["commits_total"] == 0:
                continue
            t = tree_measures(tmp, sha)
            iac_set = t.pop("_iac_set")
            ci_set = t.pop("_ci_set")
            r.update(t)
            r["iac_change_share"] = (sum(1 for c in human if any(p in iac_set for _, _, p in c["files"]))
                                     / len(human)) if human else np.nan
            r["ci_change_share"] = (sum(1 for c in human if any(p in ci_set for _, _, p in c["files"]))
                                    / len(human)) if human else np.nan
            # API-based window measures
            if use_api:
                r["merged_prs"] = merged_pr_count(full_name, a, b)
                r["ci_runs"] = ci_run_count(full_name, a, b)
            else:
                r["merged_prs"] = r["ci_runs"] = np.nan
            weeks = (b - a).days / 7
            r["ci_runs_per_week"] = r["ci_runs"] / weeks if not pd.isna(r["ci_runs"]) else np.nan
            if agent is not None and a < aidev_cutoff:
                n_agent = int(((agent["merged_at"] >= a) & (agent["merged_at"] < b)).sum())
                r["agent_merged_prs"] = n_agent
                r["agent_pr_share"] = (n_agent / r["merged_prs"]
                                       if r["merged_prs"] and not pd.isna(r["merged_prs"]) else np.nan)
            else:
                r["agent_merged_prs"] = r["agent_pr_share"] = np.nan   # window after AIDev coverage ends
            r.update(score_window(r, cfg))
            r.update({k: v for k, v in (meta or {}).items() if k in ("stars", "language", "created_at",
                                                                     "owner_type", "size_mb")})
            r.update(sc)
            r["include"] = int(r["core_devs"] >= cfg["MIN_CORE_DEVS"] and r["ksloc"] >= cfg["MIN_KSLOC"])
            rows.append(r)
        df = pd.DataFrame(rows)
        # robustness: effort over 6-month windows (the window length validated by Robles et al.)
        six = []
        for label, a, b in make_windows(cfg["START"], cfg["END"], 6):
            hc = [c for c in commits if a <= c["date"] < b and author_kind(c["name"], c["email"]) == "human"]
            if hc:
                e = effort_for_period(hc, 6, cfg)
                e.update(repo=full_name, half=label, commits_human=len(hc),
                         ksloc=sum(sum(x for x, _, p in c["files"] if file_class(p) == "src") for c in hc
                                   if sum(x for x, _, p in c["files"] if file_class(p) == "src")
                                   <= cfg["BULK_COMMIT_LINES"]) / 1000.0)
                six.append(e)
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)
        os.makedirs(os.path.join(cfg["OUT_DIR"], "repos_6m"), exist_ok=True)
        pd.DataFrame(six).to_csv(out_csv.replace("/repos/", "/repos_6m/"), index=False)
        df.to_csv(out_csv, index=False)
        print(f"  done {full_name}: {len(df)} windows, {df['include'].sum() if len(df) else 0} included, "
              f"{(time.time() - t0)/60:.1f} min")
        return df
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def score_window(r, cfg):
    """Turn raw indicators into 0-1 driver scores and COCOMO levels."""
    f = cfg["FULL_SCORE_AT"]
    s = {}
    # CI run counts are NOT used: the GitHub API keeps run history for about one year only
    s["DVOP"] = mean_avail([r["has_ci"], r["has_test_in_ci"], cap(r["n_ci_workflows"], f["n_ci_workflows"]),
                            cap(r["releases_per_month"], f["releases_per_month"])])
    s["AIAD"] = mean_avail([cap(r["agent_pr_share"], f["agent_pr_share"]),
                            cap(r["ai_commit_share"], f["ai_commit_share"]), r["has_ai_config"]])
    s["MSVC"] = min(1.0, math.log(r["n_services"]) / math.log(f["n_services"]))
    s["CLAU"] = mean_avail([int(r["n_iac_files"] > 0), cap(r["iac_change_share"], f["iac_change_share"]),
                            r["ci_deploy"]])
    s["MTEX"] = cap(r["tenure_months"], f["tenure_months"])
    s["SECU"] = mean_avail([r["has_security_policy"], r["has_dep_update"], r["has_sast"], r["has_codeowners"]])
    for k in list(s):
        s[f"{k}_level"] = to_level(s[k], cfg["LEVEL_CUTS"])
    return s
