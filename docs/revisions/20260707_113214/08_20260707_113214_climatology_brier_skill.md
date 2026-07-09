# Climatology and Brier Skill Audit

The 2022-2023 holdout contains 22510 rows and
356 positives, with prevalence
0.015815.

The null climatology Brier score is
`pi * (1 - pi) = 0.015565`.

All probability models have Brier scores close to, and slightly worse than, this
rare-event climatology baseline. Therefore the manuscript should not claim
general calibration superiority. PR-AUC should be read relative to the low
prevalence baseline, and Bayesian value should be framed as posterior rank and
threshold decision support.
