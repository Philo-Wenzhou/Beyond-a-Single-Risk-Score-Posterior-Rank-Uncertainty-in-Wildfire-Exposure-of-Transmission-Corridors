# Revision Summary

Date: 2026-07-07

Submission-clean target: EarthArXiv V1 preprint.

## Files Produced

- `manuscript/main_submission_clean.tex`
- `manuscript/main_submission_clean.pdf`
- `references_wildfire_exposure_verified.bib`
- `REVISION_SUMMARY.md`
- `SUBMISSION_CHECKLIST.md`

## Citation Integration

- Added `natbib` author-year citations.
- Integrated only keys present in `references_wildfire_exposure_verified.bib`.
- Added bibliography commands using `plainnat`.
- Compiled with `pdflatex -> bibtex -> pdflatex -> pdflatex`.
- Final BibTeX run reports zero warnings.

## Core Framing

The manuscript is now framed as a retrospective, public-data, external wildfire
exposure-ranking study for transmission-line receptor assets. It does not claim
ignition prediction, equipment failure prediction, outage prediction, damage
prediction, or legal responsibility attribution.

## Provenance Findings

- Feature-core selection provenance: no repository evidence was found showing
  that the selected physics-guided feature core was locked before inspecting the
  2022--2023 holdout. The manuscript therefore does not call it
  pre-specified and states that the temporal comparison is a retrospective
  model comparison rather than a locked final-test estimate.
- Deterministic weight provenance: the weights `0.56 dryness + 0.30 fuel +
  0.14 elevation` are fixed heuristic comparator weights in the source code.
  No training-only fitting procedure or holdout optimization script was found.
  The manuscript states that they were not optimized on the 2022--2023 holdout.

## Probability Baselines

- Training rows: 56,275.
- Training positives: 1,975.
- `pi_train = 0.0350955`.
- Holdout rows: 22,510.
- Holdout positives: 356.
- `pi_test = 0.0158152`.
- Primary Brier baseline: the out-of-sample constant probability equal to
  `pi_train`, with holdout Brier score `0.0159368`.
- Hindsight holdout-prevalence constant reference: `0.0155651`; reported only
  as a non-deployable reference.

## LANDFIRE and Model-Rerun Finding

- LANDFIRE CH and CBH are decoded as raw / 10.
- LANDFIRE CBD is decoded as raw / 100.
- The selected Bayesian/L2 linear core standardizes CH, CBH, and CBD before
  fitting, so positive constant rescaling does not change the selected-core
  standardized linear predictions.
- Selected-core model outputs were not rerun solely for decoded unit labels.
- The no-rerun statement does not apply to threshold rules or tree models.
- FBFM40 remains categorical and is not used in the selected Bayesian/L2 core.
- No ablation result that uses continuous FBFM40 remains in the clean manuscript.

## Figure and Text Cleanup

- Rebuilt the Bayesian workflow figure so the decision block uses plain labels
  for posterior exceedance and posterior top-decile membership instead of
  unrendered LaTeX-like formula strings.
- Regenerated LANDFIRE covariate layers with decoded CH/CBH/CBD units.
- Regenerated covariate diagnostic distributions with decoded canopy height.
- Split the posterior decision map into a main full-region 3-panel figure and
  an appendix high-rank-corridor zoom figure.
- Moved Stan MCMC out of the main model-family comparison and described it as
  a computational sensitivity check.

## 2026-07-07 Final Method-Reproducibility Pass

- Added exact segment construction details: WGS84 study box
  `(-123.2, 38.6, -119.0, 41.8)`, EPSG:3310 vector processing, 1,000 m
  chainage splits, retained positive-length terminal residuals, multipart
  LineString handling, and EPSG:3310 1 km buffers.
- Added the exact Bayesian/L2 design vector from the source code: 13 raw
  covariates plus `phys_dryness_index`, `phys_fuel_structure_index`, and
  `phys_dryness_x_fuel`.
- Clarified that `d_it` and `f_i` are linear composites of raw standardized
  covariates, so individual coefficients are not interpreted; the nonlinear
  physics-guided information enters through `d_it f_i`.
- Added the missing deterministic-score chain
  `r_det -> clipped/scaled s_det -> calibrated p_det`.
- Added a baseline implementation table for Logistic L2, balanced random
  forest, balanced extra trees, and histogram gradient boosting, including
  class handling, fixed parameters, and seed.
- Added paired segment-cluster bootstrap method text with `B=120` and
  percentile intervals.
- Added posterior rank-uncertainty decision-set evidence:
  stable top-decile = 781 segments, rank-uncertain = 708 segments, stable lower
  rank = 9,766 segments; point top-decile vs `rho >= 0.9` Jaccard = 0.694.
- Added `\FloatBarrier` and `\clearpage` before the bibliography so appendix
  figures cannot interrupt references.
