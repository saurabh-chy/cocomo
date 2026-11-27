# Audit of the analysis and manuscript (27 Nov 2026)

Every number in the manuscript was checked against `analysis/out/`. Extra checks are in `analysis/audit_checks.py` (outputs: `audit_checks.csv`, `rq2_att_unfiltered.csv`).

## Checks that confirmed the results

| Check | Result |
| --- | --- |
| Within vs between decomposition (Mundlak) of the quarter model | Within-repository effects equal the main quarter estimates: DVOP 1.26, CLAU 1.14, MTEX 0.56, AIAD 0.94, size exponent 0.195. The quarter-level effects are changes inside repositories |
| Is the experience effect built into the effort measure? | Controlling for the share of non-core contributors leaves MTEX at 0.58 (others change by at most 0.03) |
| AI adoption without the inclusion rules (595 repositories) | Effort +3.3% (-3.4, +9.5); size +34.7% (+9.7, +63.0); productivity +30.3% (+10.4, +54.4). Same conclusion |
| Security score vs OpenSSF Scorecard | Spearman 0.60, 275 repositories |

## Problems found and fixed in the manuscript

| Problem | Fix |
| --- | --- |
| The claim that repositories with mature cloud automation need about 20% less total effort is not robust: 0.80 (interval to 1.03) at repository level, 1.00 in the decomposition | Results 4.3, Discussion 5.2 and Conclusion now say the data show a cost during adoption but no clear saving afterwards |
| Between-repository AI estimates are unstable (1.06 vs 0.45), driven by when repositories were active | Reported as unstable and not interpreted |
| Table 6 text said one exception; there are two in company-led repositories (AIAD 1.06, SECU 0.98) | Text corrected |
| Missing method details: AIDev version, Scorecard cross-check, subgroup definitions, COCOMO default applied to quarters, company-led rule | Added to Section 3 |
| New robustness results not reported | Decomposition rows added to Table 6; unfiltered AI rows added to Table 7; churn check added to text |
| Figure 1 colour-bar label | Now "Repository-quarters (count)" |
| A table header could be stranded at a page end | Tables kept on one page |

## Revision after the publishability review (2026-11-27)

1. **Related work.** Added Agarwal, He & Vasilescu (MSR 2026), He et al. (MSR 2026) and Song, Agarwal & Wen (ISR). RQ2 is repositioned: those studies measure output, velocity and quality; this paper measures effort in person-months and separates staffing from delivered code.
2. **Effort measure is close to a head count.** ln(active developers) explains 89% of the variance in ln(PM) (78% within repositories). The paper no longer reports "effort follows the team" as a finding. The size result is reframed as: within a repository, active developers rise with KSLOC by an exponent of 0.17 and PM per developer by 0.03, so staffing is stable while delivered code varies. Hours are not observed (new limitation in Section 6.1).
3. **AI decomposition.** After adoption: active developers +2.3% (−4.0, +8.7), PM per developer −1.5% (−4.0, +1.6), human commits per developer +4.7% (−3.3, +14.3), KSLOC per developer +26.7% (+12.8, +43.6). Same people, same commit rhythm, larger contributions.
