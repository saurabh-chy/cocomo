# ===================== CHOOSE THE PILOT REPOSITORIES =====================
def eligible(m, cfg):
    ok = (m is not None and not m["fork"] and not m["archived"]
            and m["stars"] >= cfg["MIN_STARS"] and m["language"] in cfg["LANGS"]
            and m["created_at"] < cfg["CREATED_BEFORE"] and m["size_mb"] <= cfg["MAX_REPO_MB"])
    if not ok:
        return False
    # activity screen: enough recent commits to have a real team (saves cloning inactive repos)
    m["recent_commits"] = commit_count_since(m["full_name"], cfg["ACTIVE_SINCE"])
    return m["recent_commits"] >= cfg["MIN_RECENT_COMMITS"]

def select_ai_repos(prs, repos, cfg, n):
    merged = (prs[prs["merged_at"].notna() & prs["repo"].notna()]
              .groupby("repo").agg(n_agent_prs=("agent", "size"), first_agent_pr=("merged_at", "min"))
              .reset_index())
    cand = merged[(merged["n_agent_prs"] >= cfg["MIN_AGENT_PRS"]) &
                  (merged["first_agent_pr"] <= pd.Timestamp(cfg["ADOPTED_BY"], tz="UTC"))]
    # use AIDev's own star counts to pre-filter, if the column can be found
    if repos is not None:
        name_col = detect_col(repos, "full_name", "repo_url", "html_url", "url")
        star_col = detect_col(repos, "star")
        if name_col and star_col:
            rr = repos[[name_col, star_col]].copy()
            rr["repo"] = rr[name_col].astype(str).str.extract(
                r"(?:github\.com/(?:repos/)?)?([^/\s]+/[^/\s]+?)(?:\.git)?/?$")[0]
            tmp = cand.merge(rr[["repo", star_col]].rename(columns={star_col: "aidev_stars"}),
                             on="repo", how="left")
            if tmp["aidev_stars"].notna().mean() > 0.5:
                cand = tmp[tmp["aidev_stars"] >= cfg["MIN_STARS"]]
    print(f"AIDev repositories with >= {cfg['MIN_AGENT_PRS']} merged agent PRs, adopted by {cfg['ADOPTED_BY']}: {len(cand)}")
    cand = cand.sample(frac=1, random_state=cfg["SEED"])
    chosen, checked = [], 0
    for _, row in cand.iterrows():
        checked += 1
        m = repo_meta(row["repo"])
        if eligible(m, cfg):
            m.update(group="ai", first_agent_pr=row["first_agent_pr"], n_agent_prs=row["n_agent_prs"])
            chosen.append(m)
            print(f"  AI repo {len(chosen)}/{n}: {m['full_name']} ({m['language']}, {m['stars']} stars)")
        if len(chosen) >= n or checked >= cfg["MAX_CANDIDATES_CHECKED"]:
            break
    return chosen

def select_control_repos(ai_chosen, aidev_repos, cfg):
    """One comparison repository per AI repository: same language, similar stars, no AIDev activity."""
    used = set(aidev_repos) | {m["full_name"] for m in ai_chosen}
    chosen = []
    for m in ai_chosen:
        lo, hi = max(cfg["MIN_STARS"], m["stars"] // 2), m["stars"] * 2
        q = (f'language:"{m["language"]}" stars:{lo}..{hi} created:<{cfg["CREATED_BEFORE"]} '
             f'pushed:>{cfg["ACTIVE_AFTER"]} fork:false archived:false')
        j = gh_get("/search/repositories", params={"q": q, "sort": "updated", "per_page": 50}, search=True)
        for it in (j or {}).get("items", []):
            fn = it["full_name"]
            if fn in used:
                continue
            c = repo_meta(fn)
            if eligible(c, cfg):
                used.add(fn)
                c.update(group="control", matched_to=m["full_name"])
                chosen.append(c)
                print(f"  control for {m['full_name']}: {fn} ({c['stars']} stars)")
                break
    return chosen
