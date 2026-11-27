const { d, p, pc, h1, runs } = require("./lib");
module.exports = [
  new d.Paragraph({ alignment: d.AlignmentType.CENTER, spacing: { after: 240 },
    children: runs("**Does Code Size Still Drive Effort? Calibrating Six Contemporary Cost Drivers for COCOMO from 597 Open-Source Repositories**", { size: 28 }) }),
  pc("Saurabh Choudhary^1^ and Sachin Malhotra^1*^"),
  pc("^1^ Krishna Institute of Engineering & Technology (KIET), Ghaziabad, Delhi-NCR, Uttar Pradesh, India"),
  pc("^*^ Corresponding author: Sachin Malhotra, Sachin.malhotra2312@gmail.com"),
  new d.Paragraph({ children: [], spacing: { after: 240 } }),

  h1("Abstract"),
  p("**Context.** COCOMO II remains the best-known parametric model for software effort. Its multipliers come from projects of the 1990s. They do not describe continuous delivery, infrastructure as code, microservices, automated security checks or AI coding agents."),
  p("**Objective.** We add six drivers for these practices to the COCOMO structure and estimate their effects from real project data."),
  p("**Method.** We mined 597 public GitHub repositories (200 that use AI coding agents and 397 matched comparisons) in quarterly windows from 2021 to mid-2026. We measured effort as full-time-equivalent developer-months from commit activity, and we measured size and the six drivers from repository artefacts. We fitted Bayesian models with priors from COCOMO II at two levels: repository-quarters (5,932) and whole repositories (386). We estimated the effect of AI adoption with a staggered difference-in-differences design, compared accuracy with five baselines, and built a simulator from the fitted model."),
  p("**Results.** Code size explained effort weakly. The size exponent was 0.20 for repository-quarters and 0.27 for whole repositories, far below the value of about 1 that COCOMO assumes. Team experience had the largest driver effect: across its full range, it cut quarterly effort by 42%. Gains in DevOps maturity and cloud automation within a repository came with 25% and 14% more effort. Stricter security practice marked repositories that needed about 50% more effort. AI adoption did not change effort, but it raised the code delivered per person-month by 29%. The extended model was more accurate than COCOMO II (mean absolute error 22.2 versus 36.5 person-months), yet only slightly better than a calibrated baseline."),
  p("**Conclusion.** In continuous development, effort follows the team more than the code. The new drivers explain effort better than they predict it. Estimators should calibrate team experience first and treat lines of code as a weak signal."),
  p("**Keywords:** software effort estimation; COCOMO II; DevOps; AI coding agents; mining software repositories; Bayesian calibration"),
];
