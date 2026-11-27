const { p, h1 } = require("./lib");
module.exports = [
  h1("7 Conclusion"),
  p("COCOMO II was calibrated before continuous delivery, cloud automation, microservices, automated security and AI coding agents became common. We added six drivers for these practices and estimated their effects from 597 public repositories, quarter by quarter, from 2021 to mid-2026."),
  p("Four findings stand out. First, code size was a weak driver of effort. The size exponent was 0.20 for quarters and 0.27 for whole repositories, far below the value that COCOMO assumes. Staffing stayed stable while the code it delivered varied widely. Because our effort measure counts active developers, this is a finding about staffing, not hours. Second, team experience was the strongest of the six drivers, with 42% less quarterly effort across its full range. Third, DevOps maturity and cloud automation raised effort while teams built them, and we found no clear saving afterwards. Fourth, AI adoption left staffing and commit rates unchanged but raised the code delivered per person-month by about 29%. This adds an effort view to recent studies that found more output and lower code quality after AI adoption. The extended model explained effort well but predicted it only slightly better than a calibrated baseline."),
  p("Future work should test these drivers on industrial projects with recorded hours, which would show whether hours follow size more closely than staffing does. It should study whether the cost of automation repays itself over a longer period than five years, and it should follow the quality of the extra code that AI tools produce. Because every measure in this study is a script, the calibration can be repeated as tools and practices change."),

  h1("Data Availability Statement"),
  p("The data, mining scripts, analysis code, figures and pilot notes are openly available at https://github.com/saurabh-chy/cocomo. An archived copy will be deposited on Zenodo with a DOI on acceptance. All raw data come from public sources: GitHub, the AIDev dataset and the OpenSSF Scorecard. The released data contain no developer names or email addresses."),
  h1("Conflict of Interest Statement"),
  p("The authors declare no conflicts of interest."),
  h1("Funding Statement"),
  p("This research received no specific grant from any funding agency in the public, commercial or not-for-profit sectors."),
  h1("Ethics Statement"),
  p("The study used only publicly available repository data. We stored no developer identities in the analysis data, and the results identify no individual developer."),
  h1("Supporting Information"),
  p("Additional supporting information can be found online in the Supporting Information section at the end of this article."),
  p("**Supporting Information S1.** Measurement rules, pilot studies and hand check, full model results, additional robustness checks and simulation details (Tables S1 to S13)."),
  p("**Supplementary Data S1.** List of the 597 repositories with selection values, matching and use in the analysis (CSV)."),
  h1("Author Contributions"),
  p("**Saurabh Choudhary:** Conceptualization, Methodology, Software, Data curation, Formal analysis, Visualization, Writing – original draft. **Sachin Malhotra:** Conceptualization, Supervision, Writing – review & editing."),
];
