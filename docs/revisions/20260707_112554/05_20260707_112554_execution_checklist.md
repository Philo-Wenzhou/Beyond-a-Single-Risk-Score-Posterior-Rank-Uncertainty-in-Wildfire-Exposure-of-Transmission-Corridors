# Execution Checklist

## Do First

- [ ] Audit LANDFIRE CH/CBH/CBD scaling in Phase 3 model-table construction.
- [ ] Audit whether FBFM40 enters models as a raw continuous variable.
- [ ] Inspect processed Phase 3 value ranges for canopy variables.
- [ ] Decide whether model outputs must be rerun.

## Then Manuscript Reframe

- [ ] Replace prospective language with retrospective annual exposure ranking.
- [ ] Remove current research-advantage heatmap from main manuscript.
- [ ] Add neutral framework taxonomy table if useful.
- [ ] Promote posterior top-decile rank probability to primary Bayesian output.
- [ ] Demote posterior exceedance probability to secondary diagnostic.
- [ ] Add rigorous fire-indexed label equation.
- [ ] State label sets are parallel, not mutually exclusive.
- [ ] Add overlap detail: electrical-only versus mixed electrical/non-electrical
  overlap, after verifying the exact count.

## Then Validation QA

- [ ] Verify M5 selection history.
- [ ] Add constant-prevalence baseline.
- [ ] Add Brier Skill Score.
- [ ] Add PR-AUC/prevalence and Lift@10.
- [ ] Generate top-k capture curve.
- [ ] Plan or run clustered bootstrap CI for metric differences.

## Then Methods Upgrade

- [ ] Define deterministic comparator exactly.
- [ ] Add calibrated deterministic probability equation.
- [ ] Add relation to L2-regularized logistic regression.
- [ ] Add Laplace approximation equations.
- [ ] Fix workflow figure formulas.
- [ ] Rebuild the Bayesian workflow figure if formulas are embedded in the
  image.

## Then Figure Pruning

- [ ] Keep main figures limited to study area, labels, workflow, validation,
  capture curve, ablation, posterior rank map, and bootstrap effect comparison.
- [ ] Move data covariate layers and diagnostics to supplement.
- [ ] Remove duplicate posterior decision map if the zoomed posterior map is
  kept.
- [ ] Remove redundant model-comparison bar figure if Table 2 and capture curve
  cover the same evidence.

## Release Gate

Before a new EarthArXiv candidate PDF:

- [ ] No P0 preprocessing blockers remain.
- [ ] Manuscript is explicitly retrospective unless prospective features are
  rebuilt.
- [ ] Holdout is not used for feature/model selection, or this is disclosed and
  corrected.
- [ ] Calibration baseline is reported.
- [ ] Top-k ranking value is shown relative to rare-event prevalence.
- [ ] All figures in the main paper support claims that remain after reframe.

