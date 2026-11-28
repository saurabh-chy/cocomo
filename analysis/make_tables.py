"""Build every computed table of the paper and its Supporting Information from analysis/out/.

Run after the analysis scripts (see reproduce.py). Writes one CSV per table to analysis/tables/
and all tables together to analysis/tables/all_tables.xlsx. Values are rounded and labelled as
in the paper, so each file can be compared with the printed table cell by cell.

Tables 1, S1-S3 (measurement rules) and S10 (simulator inputs) are definitions, not results; the
rules live in pipeline/core.py and pipeline/run.py, and the simulator inputs in rq4_sim.py.
Tables S4-S5 report the pilots and the hand check; see docs/pilot_log.md.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
TAB = os.path.join(HERE, "tables")
DATA = os.path.join(HERE, "..", "data", "full_run")
os.makedirs(TAB, exist_ok=True)

DR = ["DVOP", "AIAD", "MSVC", "CLAU", "MTEX", "SECU"]
NAME = {"DVOP": "DevOps maturity", "AIAD": "AI assistance", "MSVC": "Microservice complexity",
        "CLAU": "Cloud automation", "MTEX": "Team experience", "SECU": "Security practice"}
MINUS = "−"


def rd(subdir, f):
    return pd.read_csv(os.path.join(subdir, f))


def num(x, d=2):
    """Fixed decimals, with a true minus sign as in the paper (and no "-0.00")."""
    s = f"{x:.{d}f}"
    if s.startswith("-"):
        s = s[1:] if float(s) == 0 else MINUS + s[1:]
    return s


def ci(est, lo, hi, d=2):
    return f"{num(est, d)} ({num(lo, d)}, {num(hi, d)})"


def pct(v):
    return 100 * (np.exp(v) - 1)


def spct(v, d=1):
    s = num(pct(v), d)
    return s if s.startswith(MINUS) or s == f"{0:.{d}f}" else "+" + s


def pct_ci(att, lo, hi):
    return f"{spct(att)}% ({spct(lo)}%, {spct(hi)}%)"


def comma(n):
    return f"{int(n):,}"


def draws(name):
    return np.load(os.path.join(OUT, f"{name}_draws.npz"), allow_pickle=True)


def post(x, d=2, ratio=False):
    lo, hi = np.quantile(x, [0.025, 0.975])
    m = x.mean()
    if ratio:
        return ci(np.exp(m), np.exp(lo), np.exp(hi), d)
    return ci(m, lo, hi, d)


def p_below(x):
    p = float(np.mean(x < 0))
    return "<0.001" if p < 0.001 else (">0.999" if p > 0.999 else f"{p:.2f}")


tables = {}


def save(key, title, df, note=""):
    tables[key] = (title, df, note)
    df.to_csv(os.path.join(TAB, f"Table_{key}.csv"), index=False, encoding="utf-8-sig")


# ---------------- Table 2: sample at each stage ----------------
s = pd.read_csv(os.path.join(DATA, "sample.csv"))
a = rd(OUT, "all_quarters.csv")
q = rd(OUT, "quarter.csv")
r = rd(OUT, "repo.csv")
cnt = lambda ser: (ser.get("ai", 0), ser.get("control", 0))
g1 = s["group"].value_counts()
g3 = q.groupby("group")["repo"].nunique()
g4 = q["group"].value_counts()
g5 = r["group"].value_counts()
save("2", "Sample at Each Stage", pd.DataFrame([
    ["Repositories selected and processed", comma(g1["ai"]), comma(g1["control"]), comma(len(s))],
    ["Repository-quarters measured", "", "", comma(len(a))],
    ["Repositories with at least one included quarter", comma(g3["ai"]), comma(g3["control"]), comma(q["repo"].nunique())],
    ["Included repository-quarters", comma(g4["ai"]), comma(g4["control"]), comma(len(q))],
    ["Repositories with at least four included quarters (repository level)", comma(g5["ai"]), comma(g5["control"]), comma(len(r))],
], columns=["Stage", "AI group", "Comparison group", "Total"]))

# ---------------- Table 3: priors (constants used in rq1_bayes.py) ----------------
save("3", "Prior Distributions for the Bayesian Models", pd.DataFrame([
    ["γ for DVOP and CLAU", f"N({num(np.log(0.78 / 1.17))}, 0.30^2)", "ln(0.78 / 1.17), TOOL range"],
    ["γ for MTEX", f"N({num(np.log(0.81 / 1.22))}, 0.30^2)", "ln(0.81 / 1.22), APEX range"],
    ["γ for SECU", f"N({num(np.log(1.26 / 0.82))}, 0.30^2)", "ln(1.26 / 0.82), RELY range"],
    ["γ for MSVC and AIAD", "N(0, 0.50^2)", "No calibrated value"],
    ["B (size exponent)", "N(1, 0.50^2)", "COCOMO II range of about 0.9 to 1.2"],
    ["ln A, controls", "N(0, 5^2), N(0, 1)", "Weakly informative"],
    ["σ, σu", "Half-normal(1)", "Weakly informative"],
], columns=["Parameter", "Prior", "Basis"]), "The vague-prior models used N(0, 10^2) for B and every γ.")

# ---------------- Table 4: descriptives ----------------
de = pd.read_csv(os.path.join(OUT, "descriptives.csv"), index_col=0)
rows = []
for k, lab, d in [("effort_pm", "Effort (PM)", 1), ("ksloc", "Size (KSLOC)", 1), ("team_size", "Team size (developers)", 1)] + \
        [(k, f"{k} score", 2) for k in DR]:
    x = de.loc[k]
    rows.append([lab] + [num(x[c], d) for c in ["mean", "50%", "std", "5%", "95%"]])
save("4", f"Descriptive Statistics of the {comma(len(q))} Included Repository-Quarters",
     pd.DataFrame(rows, columns=["Variable", "Mean", "Median", "SD", "5th pct", "95th pct"]))

# ---------------- Table 5: posterior effort ratios at two levels ----------------
R = draws("rq1_repo_literature_duration")
Q = draws("rq1_quarter_literature")
rows = [[NAME[k], post(R[k], ratio=True), p_below(R[k]), post(Q[k], ratio=True), p_below(Q[k])] for k in DR]
rows += [["Size exponent B", post(R["B"]), "", post(Q["B"]), ""],
         ["Residual SD σ", num(R["sigma"].mean()), "", num(Q["sigma"].mean()), ""],
         ["Repository SD σu", "", "", num(Q["sigma_repo"].mean()), ""],
         ["Observations", f"{comma(len(r))} repositories", "", f"{comma(len(q))} quarters", ""]]
save("5", "Posterior Effort Ratios for the Six Drivers at Two Levels", pd.DataFrame(rows, columns=[
    "Parameter", "Repository level: ratio (95% CrI)", "P(ratio < 1)", "Quarter level: ratio (95% CrI)", "P(ratio < 1)"]))

# ---------------- Table 6: robustness of quarter-level effects ----------------
rob = rd(OUT, "robustness.csv")
au = rd(OUT, "audit_checks.csv")
lab6 = {"Main (theta = 12)": "Main (θ = 12)", "Effort, theta = 17": "Effort with θ = 17",
        "Effort, theta = 24": "Effort with θ = 24", "Effort, active days": "Effort by active days"}
rows = []
for _, x in rob.iterrows():
    lab = lab6.get(x["variant"], x["variant"])
    if x["variant"].startswith(("Company", "Community")):
        lab = f"{x['variant'].split()[0]} ({comma(x['repos'])} repositories)"
    rows.append([lab, num(x["ln_ksloc"])] + [num(np.exp(x[k])) for k in DR])
mu = au[au["check"] == "mundlak"].set_index(["term", "part"])["coef"]
for part, lab in [("w", "Within-repository part"), ("m", "Between-repository part")]:
    rows.append([lab, num(mu[("ln_ksloc", part)])] + [num(np.exp(mu[(k, part)])) for k in DR])
save("6", "Robustness of the Quarter-Level Effects", pd.DataFrame(rows, columns=["Variant", "B"] + DR))

# ---------------- Table 7: difference-in-differences ----------------
att = pd.concat([rd(OUT, "rq2_att.csv"), rd(OUT, "rq2_att_unfiltered.csv")])
lab7 = {("all", "ln_pm"): "All: effort", ("all", "ln_ksloc"): "All: size (KSLOC)",
        ("all", "ln_prod"): "All: productivity (KSLOC/PM)", ("company-led", "ln_pm"): "Company-led: effort",
        ("community", "ln_pm"): "Community: effort", ("experienced teams", "ln_pm"): "Experienced teams: effort",
        ("less experienced teams", "ln_pm"): "Less experienced teams: effort",
        ("unfiltered", "ln_pm"): "No inclusion rules: effort", ("unfiltered", "ln_ksloc"): "No inclusion rules: size (KSLOC)",
        ("unfiltered", "ln_prod"): "No inclusion rules: productivity"}
rows = []
for key, lab in lab7.items():
    x = att[(att["subset"] == key[0]) & (att["outcome"] == key[1])].iloc[0]
    rows.append([lab, pct_ci(x["att"], x["ci_low"], x["ci_high"]), pct_ci(x["pre_avg"], x["pre_ci_low"], x["pre_ci_high"]),
                 f"{int(x['n_treated_repos'])} / {int(x['n_never'])}"])
save("7", "Effect of AI Adoption (Staggered Difference-in-Differences)", pd.DataFrame(rows, columns=[
    "Sample and outcome", "Effect after adoption (95% CI)", "Gap before adoption (95% CI)", "Adopters / never-adopters"]))

# ---------------- Table 8: accuracy ----------------
acc = rd(OUT, "rq3_accuracy.csv")
te = rd(OUT, "rq3_tests.csv").set_index("baseline")
rows = []
for _, x in acc.iterrows():
    dm = "–"
    if x["model"] in te.index:
        t = te.loc[x["model"]]
        dm = f"{num(t['mae_diff'])} ({num(t['diff_ci_low'])}, {num(t['diff_ci_high'])})"
    rows.append([x["model"], num(x["MAE"]), num(x["MdAE"]), num(x["SA_pct"], 1), num(x["glass_delta"], 1),
                 num(x["pred25"], 1), "–" if pd.isna(x["pi90_coverage"]) else num(x["pi90_coverage"], 1), dm])
save("8", "Accuracy of Six Models in Grouped 10-Fold Cross-Validation", pd.DataFrame(rows, columns=[
    "Model", "MAE (PM)", "MdAE (PM)", "SA (%)", "Glass's Δ", "Pred (25) (%)", "90% PI cover (%)", "MAE minus Extended, PM (95% CI)"]),
    "Confidence intervals from 2,000 bootstrap samples of repositories. Repository-level tests: Supplementary Table S17.")

# ---------------- Table 9: Sobol indices ----------------
so = rd(OUT, "rq4_sobol.csv").sort_values("S1", ascending=False)
lab9 = {"ln_KSLOC": "ln KSLOC", **NAME}
rows = []
for _, x in so.iterrows():
    if x["S1"] < 0.005:
        rows.append([lab9[x["input"]], "<0.01", "<0.01"])
    else:
        rows.append([lab9[x["input"]], ci(x["S1"], x["S1"] - x["S1_conf"], x["S1"] + x["S1_conf"]), num(x["ST"])])
save("9", "Sobol Sensitivity Indices for Log Effort", pd.DataFrame(rows, columns=["Input", "First-order index (95% CI)", "Total index"]))

# ---------------- Table 10: size-only bias ----------------
bi = rd(OUT, "rq4_sizeonly_bias.csv").set_index("profile")
order = [("All projects", "All quarters")] + [(p, p) for p in [
    "Experienced team (MTEX at or above 75th pct)", "New team (MTEX at or below 25th pct)",
    "High automation (DVOP and CLAU at or above 75th pct)", "Microservices (MSVC above 0)", "Heavy AI use (AIAD at least 0.3)"]]
rows = []
for k, lab in order:
    x = bi.loc[k]
    rows.append([lab, comma(x["n"]), num(x["median_ratio_estimate_to_actual"]), num(x["share_off_by_more_than_25pct"], 1)])
save("10", "Bias of a Size-Only Model on Simulated Quarters, by Project Profile", pd.DataFrame(rows, columns=[
    "Profile", "Simulated quarters", "Median estimate / actual", "Off by more than 25% (%)"]))

# ---------------- Tables S6 and S7: full posterior results ----------------
LANG = ["Python", "Java", "Go", "TypeScript", "JavaScript", "Rust", "Unknown"]


def coef_rows(D, extra=()):
    names = list(D["control_names"])
    C = D["controls"]
    col = lambda n: C[:, names.index(n)]
    out = [["ln A", post(D["lnA"])], ["B (ln KSLOC)", post(D["B"])]] + [[k, post(D[k])] for k in DR]
    for n, lab in extra:
        out.append([lab, post(col(n)) if n in names else "–"])
    out += [["Company-led", post(col("company_led"))], ["Repository age (SD)", post(col("age_years"))],
            ["Bot commit share", post(col("bot_share"))]]
    out += [[f"Language: {l if l != 'Unknown' else 'unknown'}", post(col(f"lang_{l}"))] for l in LANG]
    return out


m1 = coef_rows(R, [("ln_quarters", "ln observed quarters")])
m2 = coef_rows(draws("rq1_repo_vague_duration"), [("ln_quarters", "ln observed quarters")])
m3 = coef_rows(draws("rq1_repo_literature"), [("ln_quarters", "ln observed quarters")])
rows = [[a_[0], a_[1], b_[1], c_[1]] for a_, b_, c_ in zip(m1, m2, m3)]
rows.append(["σ"] + [post(draws(n)["sigma"]) for n in ["rq1_repo_literature_duration", "rq1_repo_vague_duration", "rq1_repo_literature"]])
dg = []
for n in ["rq1_repo_literature_duration", "rq1_repo_vague_duration", "rq1_repo_literature"]:
    sm = rd(OUT, n + ".csv")
    dg.append(f"{sm['r_hat'].max():.3f} / {comma(round(sm['ess_bulk'].min()))}")
rows.append(["Maximum R-hat / minimum bulk ESS"] + dg)
save("S6", f"Repository-Level Models (n = {comma(len(r))}): Posterior Means and 95% Credible Intervals",
     pd.DataFrame(rows,
                  columns=["Parameter", "Main (literature priors)", "Vague priors", "Without observed-quarters control"]))

QV = draws("rq1_quarter_vague")
k1, k2 = coef_rows(Q), coef_rows(QV)
rows = [[a_[0], a_[1], b_[1]] for a_, b_ in zip(k1, k2)]
rows += [["σ (residual)", post(Q["sigma"]), post(QV["sigma"])], ["σu (repository)", post(Q["sigma_repo"]), post(QV["sigma_repo"])]]
diag = []
for f in ["rq1_quarter_literature.csv", "rq1_quarter_vague.csv"]:
    sm = rd(OUT, f)
    diag.append(f"{sm['r_hat'].max():.3f} / {comma(round(sm['ess_bulk'].min()))}")
rows.append(["Maximum R-hat / minimum bulk ESS"] + diag)
save("S7", f"Repository-Quarter Models (n = {comma(len(q))} from {q['repo'].nunique()} Repositories): Posterior Means and 95% Credible Intervals",
     pd.DataFrame(rows, columns=["Parameter", "Main (literature priors)", "Vague priors"]))

# ---------------- Table S8: within/between and turnover control ----------------
mu = au[au["check"] == "mundlak"].set_index(["term", "part"])
nc = au[au["check"] == "noncore_control"].set_index("term")


def wald(c, se, d=2, ratio=True):
    lo, hi = c - 1.96 * se, c + 1.96 * se
    return ci(np.exp(c), np.exp(lo), np.exp(hi), d) if ratio else ci(c, lo, hi, d)


rows = [["B (ln KSLOC)", wald(*mu.loc[("ln_ksloc", "w"), ["coef", "se"]], 3, False),
         wald(*mu.loc[("ln_ksloc", "m"), ["coef", "se"]], 3, False), "–"]]
for k in DR:
    rows.append([NAME[k], wald(*mu.loc[(k, "w"), ["coef", "se"]]), wald(*mu.loc[(k, "m"), ["coef", "se"]]),
                 wald(*nc.loc[k, ["coef", "se"]])])
save("S8", "Within/Between Decomposition and Control for Contributor Turnover (Effort Ratios, 95% CI)",
     pd.DataFrame(rows, columns=["Variable", "Within repositories", "Between repositories", "With non-core share control"]))

# ---------------- Table S9: event study ----------------
ev = rd(OUT, "rq2_event_study.csv")


def evcell(e, y):
    x = ev[(ev["e"] == e) & (ev["outcome"] == y)]
    if x.empty:
        return "0"
    x = x.iloc[0]
    return f"{num(pct(x['att']), 1)} ({num(pct(x['ci_low']), 1)}, {num(pct(x['ci_high']), 1)})"


rows = []
for e in range(-6, 5):
    lab = "−1 (reference)" if e == -1 else num(e, 0)
    rows.append([lab] + (["0", "0", "0"] if e == -1 else [evcell(e, y) for y in ["ln_pm", "ln_ksloc", "ln_prod"]]))
save("S9", "Event-Study Estimates of AI Adoption, % Change (95% CI)", pd.DataFrame(rows, columns=[
    "Quarter relative to adoption", "Effort", "Size (KSLOC)", "Productivity (KSLOC/PM)"]))

# ---------------- Table S11: simulator validation ----------------
va = rd(OUT, "rq4_validation.csv")
nhold = int((q["quarter"].str[:4].astype(int) >= 2025).sum())
save("S11", f"Observed and Simulated Quarterly Effort, 2025 to 2026 ({comma(nhold)} Quarters)", pd.DataFrame(
    [[f"{int(round(100 * x['quantile']))}th", num(x["observed_pm"], 1), num(x["simulated_pm"], 1)] for _, x in va.iterrows()],
    columns=["Percentile", "Observed (PM)", "Simulated (PM)"]))

# ---------------- Table S12: scenarios ----------------
sc = rd(OUT, "rq4_scenarios.csv")
save("S12", "Effort Ratio When One Driver Moves From Its 10th to Its 90th Percentile", pd.DataFrame(
    [[NAME[x["driver"]], f"{num(x['from'])} to {num(x['to'])}", num(x["effort_ratio_median"], 3),
      f"{num(x['ci90_low'], 3)} to {num(x['ci90_high'], 3)}"] for _, x in sc.iterrows()],
    columns=["Driver", "Score change", "Median ratio", "90% interval"]),
    "AI assistance from 0 to 0.5: ratio {} (95% interval {} to {}).".format(
        *[num(v) for v in np.exp(0.5 * np.array([np.median(Q["AIAD"]), *np.quantile(Q["AIAD"], [0.025, 0.975])]))]))

# ---------------- Table S13: attenuation ----------------
at = rd(OUT, "rq4_attenuation.csv").pivot(index="driver", columns="error_sd", values="retained_pct")
save("S13", "Share of Each Estimated Effect Retained Under Measurement Error in the Driver Scores (%)", pd.DataFrame(
    [[NAME[k]] + [num(at.loc[k, sd], 0) for sd in [0.05, 0.10, 0.20]] for k in ["MTEX", "DVOP", "AIAD", "CLAU", "MSVC", "SECU"]],
    columns=["Driver", "Error SD 0.05", "Error SD 0.10", "Error SD 0.20"]))

# ---------------- Table S14: what the effort measure counts ----------------
ec = rd(OUT, "effort_construct.csv")
lab14 = {"Effort on active developers": "ln effort on ln active developers", "Effort on size": "ln effort on ln KSLOC",
         "Active developers on size": "ln active developers on ln KSLOC",
         "Effort per developer on size": "ln effort per developer on ln KSLOC"}
rows = []
for m, lab in lab14.items():
    p_ = ec[(ec["model"] == m) & (ec["level"] == "Pooled")].iloc[0]
    w_ = ec[(ec["model"] == m) & (ec["level"] == "Within repository")].iloc[0]
    rows.append([lab, ci(p_["slope"], p_["ci_lo"], p_["ci_hi"]), num(p_["r2"]), ci(w_["slope"], w_["ci_lo"], w_["ci_hi"]), num(w_["r2"])])
save("S14", f"Effort, Active Developers and Size in {comma(len(q))} Repository-Quarters (Least-Squares Slopes, 95% CI)",
     pd.DataFrame(rows, columns=["Model", "Pooled: slope (95% CI)", "Pooled R2", "Within repository: slope (95% CI)", "Within R2"]))

# ---------------- Table S15: AI adoption and the parts of effort ----------------
co = rd(OUT, "rq2_components.csv")
save("S15", "Effect of AI Adoption on the Parts of Effort and on Commit Volume", pd.DataFrame(
    [[x["label"], pct_ci(x["att"], x["ci_low"], x["ci_high"]), pct_ci(x["pre_avg"], x["pre_ci_low"], x["pre_ci_high"])]
     for _, x in co.iterrows()], columns=["Outcome", "Effect after adoption (95% CI)", "Gap before adoption (95% CI)"]))

# ---------------- Table S16: alternative adoption definitions ----------------
tr = rd(OUT, "rq2_treatment.csv")
lab16 = {"ln_pm": "Effort", "ln_team": "Active developers", "ln_ksloc": "Size (KSLOC)", "ln_prod": "Productivity"}
rows = []
for name in tr["subset"].unique():
    for y, ylab in lab16.items():
        x = tr[(tr["subset"] == name) & (tr["outcome"] == y)].iloc[0]
        rows.append([name if y == "ln_pm" else "", ylab, pct_ci(x["att"], x["ci_low"], x["ci_high"]),
                     pct_ci(x["pre_avg"], x["pre_ci_low"], x["pre_ci_high"]),
                     f"{int(x['n_treated_repos'])} / {int(x['n_never'])}" if y == "ln_pm" else ""])
cn = pd.read_csv(os.path.join(OUT, "rq2_treatment_counts.csv"), index_col=0)
save("S16", "Effect of AI Adoption Under Alternative Definitions of Adoption", pd.DataFrame(rows, columns=[
    "Definition", "Outcome", "Effect after adoption (95% CI)", "Gap before adoption (95% CI)", "Adopters / never-adopters"]),
    f"Main sample: {cn.loc['Adopters (any signal)', 'AI group (AIDev)']} adopters from the AI group and "
    f"{cn.loc['Adopters (any signal)', 'Comparison group']} from the comparison group; all "
    f"{cn.loc['Never adopted'].sum()} never-adopters are comparison repositories. Repositories with a signal that a definition does not use are excluded from that row.")

# ---------------- Table S17: repository-clustered accuracy tests ----------------
te = rd(OUT, "rq3_tests.csv")
order17 = ["COCOMO II (default)", "Size-only (linear)", "COCOMO II (recalibrated)", "ATLM", "Random forest"]
rows = []
for m in order17:
    t = te[te["baseline"] == m].iloc[0]
    pf = lambda v: "<0.001" if v < 0.001 else f"{v:.3f}"
    rows.append([m, f"{num(t['mae_diff'])} ({num(t['diff_ci_low'])}, {num(t['diff_ci_high'])})", pf(t["p_boot"]),
                 num(t["A12_repo"]), pf(t["p_holm"]), num(t["A12"]), pf(t["p_quarter_level"])])
save("S17", "Comparison of Each Baseline With COCOMO-Extended, Accounting for Repository Clustering", pd.DataFrame(rows, columns=[
    "Baseline", "MAE difference, PM (95% cluster CI)", "Bootstrap p", "Repository A12", "Repository Wilcoxon p (Holm)",
    "Quarter A12", "Quarter Wilcoxon p (unadjusted)"]),
    "482 repositories. Positive differences and A12 above 0.5 favour COCOMO-Extended. Repository tests compare repository mean absolute errors (one pair per repository). Quarter-level columns treat the 5,932 quarters as independent and are shown for comparison only.")

# ---------------- one workbook ----------------
with pd.ExcelWriter(os.path.join(TAB, "all_tables.xlsx")) as xw:
    idx = pd.DataFrame([[f"Table {k}", t] for k, (t, _, _) in tables.items()], columns=["Sheet", "Title"])
    idx.to_excel(xw, sheet_name="Index", index=False)
    for k, (t, df, note) in tables.items():
        sh = f"Table {k}"
        pd.DataFrame([[t]]).to_excel(xw, sheet_name=sh, index=False, header=False)
        df.to_excel(xw, sheet_name=sh, index=False, startrow=2)
        if note:
            pd.DataFrame([[f"Note. {note}"]]).to_excel(xw, sheet_name=sh, index=False, header=False, startrow=len(df) + 4)
print(f"wrote {len(tables)} tables to {TAB}")
