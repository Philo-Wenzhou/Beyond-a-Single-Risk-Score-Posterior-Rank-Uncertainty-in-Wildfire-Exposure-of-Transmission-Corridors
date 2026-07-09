# Project Memory

Last updated: 2026-07-03

## Active Framing

This project is a reproducible California public-data pipeline for
physics-informed Bayesian wildfire exposure ranking of transmission-line
segments.

Use this framing consistently:

- Transmission lines are receptor assets, not assumed ignition sources.
- The main label is external/exogenous wildfire exposure.
- CAL FIRE `Electrical Power` cause is excluded from the main exposure label to
  avoid circular attribution.
- The decision outputs are posterior probabilities:
  `P(exposure > threshold)` and `P(rank in top 10%)`.
- Do not frame the study as powerline ignition prediction, equipment failure
  prediction, or outage prediction.

Active project path:

```text
Bayesian_Wildfire_Exposure_CA
```

Study design:

```text
Region: Northern Sierra / Southern Cascades, California
Panel: segment-year, 2017-2023
Train years: 2017-2021
Temporal holdout: 2022-2023
Main label: exogenous_fire_exposure
Segments: 11,255
Segment-year rows: 78,785
```

## Data Pipeline

Core public data sources:

- CEC transmission lines.
- CAL FIRE fire perimeters and cause fields.
- gridMET annual weather and fuel-moisture summaries.
- USGS 3DEP DEM.
- LANDFIRE LFPS fuel and canopy layers.

Key processed assets:

```text
data/processed/phase1/segments_1km.gpkg
data/processed/phase1/segment_buffers_1km.gpkg
data/processed/phase1/segment_year_labels_2017_2023.csv
data/processed/phase3/segment_year_model_table.parquet
```

Phase 1 label counts:

- all-fire exposure positives: 3,187;
- exogenous exposure positives: 2,331;
- strict exposure positives: 2,075;
- electrical-power overlap positives: 885.

## Modeling Features

Selected physics-informed core:

```text
gridmet_vpd_p95
gridmet_erc_p95
gridmet_bi_p95
gridmet_vs_p95
gridmet_fm100_p05
gridmet_fm1000_p05
gridmet_rmin_p05
gridmet_pr_sum
dem_elevation_m
landfire_canopy_cover_pct
landfire_canopy_height_m
landfire_canopy_base_height_m
landfire_canopy_bulk_density
phys_dryness_index
phys_fuel_structure_index
phys_dryness_x_fuel
```

The deterministic baseline is a calibrated public physics score. It is a
transparent comparator, not the final decision model.

## Current Results

Temporal holdout results for 2022-2023:

| Model | ROC-AUC | PR-AUC | Brier | Row top-10% capture | Segment top-10% capture |
|---|---:|---:|---:|---:|---:|
| ML logistic L2 | 0.663 | 0.039 | 0.015713 | 0.289 | 0.216 |
| Bayesian Laplace | 0.662 | 0.038 | 0.015718 | 0.289 | 0.216 |
| Stan MCMC pilot | 0.662 | 0.038 | 0.015710 | 0.289 | 0.216 |
| Deterministic calibrated | 0.651 | 0.028 | 0.015734 | 0.219 | 0.118 |
| Balanced extra trees | 0.617 | 0.022 | 0.056091 | 0.180 | 0.104 |
| Histogram gradient boosting | 0.553 | 0.019 | 0.016647 | 0.132 | 0.149 |
| Balanced random forest | 0.568 | 0.018 | 0.034539 | 0.107 | 0.152 |

Core interpretation:

- Bayesian/Laplace and Stan MCMC agree closely.
- Deterministic calibrated score is weaker for rare-event PR-AUC and top-decile
  capture.
- Flexible tree ML does not automatically generalize better under temporal
  holdout.
- Dynamic gridMET weather drives most discrimination; LANDFIRE static fuel alone
  is weak.
- The Bayesian value is not just point prediction; it is posterior exceedance
  and posterior rank probability for extreme-disaster triage.

## Stan Notes

Current CmdStan root:

```text
F:\Rprogram\WeiPHD\.cmdstan_local\cmdstan-2.38.0
```

`cmdstanpy` is reused from:

```text
E:\WPSDrive\198731884\WPS云盘\WeiPHD\.python_deps
```

Project-local `scripts/mingw32-make.exe` maps RTools 45 `make.exe` to the name
CmdStan expects.

Pilot MCMC command:

```powershell
C:\anaconda3\python.exe scripts\phase6_run_stan_mcmc.py --chains 2 --parallel-chains 2 --warmup 200 --sampling 200 --suffix pilot
```

If `cmdstanpy` cannot decode CSV metadata under local non-UTF-8 paths, extract
`p_new[...]` directly:

```powershell
C:\anaconda3\python.exe scripts\phase6_extract_stan_csv.py --suffix pilot
```

## Figure Style

Use SCI-style restrained figures:

- no saturated red/purple palettes;
- no low-contrast or unclear basemap legends;
- maps should not look like tilted rectangular frames;
- use muted paper background, dark text, teal/gold accents, and clear legends.

Key figure outputs:

```text
outputs/figures/phase4/phase4_temporal_holdout_validation.png
outputs/figures/phase4/phase4_deterministic_vs_bayesian_ranking.png
outputs/figures/phase4/phase4_decision_metric_maps.png
outputs/figures/phase5/phase5_ablation_validation_metrics.png
outputs/figures/phase6/phase6_model_comparison_metrics.png
outputs/figures/phase6/phase6_stan_mcmc_decision_maps.png
outputs/figures/phase8/phase8_faceted_zoom_posterior_maps.png
outputs/figures/phase8/phase8_research_advantage_matrix.png
outputs/figures/phase8/phase8_bayesian_method_schematic.png
outputs/figures/phase8/phase8_gridmet_model_covariates_2021.png
outputs/figures/phase8/phase8_dem_model_covariate.png
outputs/figures/phase8/phase8_landfire_model_covariates.png
outputs/figures/phase8/phase8_model_aligned_environmental_covariates.png
```

Manuscript-ready result tables:

```text
outputs/tables/manuscript_core_results.csv
outputs/tables/manuscript_core_results.md
docs/manuscript_results_summary.md
```

LaTeX manuscript scaffold:

```text
manuscript/main.tex
manuscript/main.pdf
manuscript/README.md
```

2026-07-03 manuscript update:

- Added faceted full-region plus zoomed posterior maps.
- Added research-advantage matrix comparing deterministic scores, tree ML,
  Bayesian ranking, and Stan MCMC.
- Added Bayesian workflow and mathematical decision schematic.
- Expanded the TeX methods section with deterministic baseline, Bayesian
  posterior, posterior aggregation, exceedance probability, and top-decile rank
  probability equations.
- Removed path-heavy reproducibility prose from the manuscript body.
- Replaced the crowded environmental preview figure with separate model-aligned
  gridMET, DEM, and LANDFIRE covariate maps. Avoid using the old raw preview
  triptych in the manuscript because it visually compresses too many panels.
- Keep public environmental covariates as an explicit background Figure 3 near
  Public Data Sources. Use a continued vertical figure group that directly
  inserts the Phase 2 source-preview files: (a)
  `outputs/figures/data_previews/phase2_gridmet_preview_2021.png`, (b)
  `outputs/figures/data_previews/phase2_dem_preview.png`, and (c)
  `outputs/figures/data_previews/phase2_landfire_preview.png`. Do not replace
  this background figure with phase8 model-aligned derivative maps unless a
  separate methods figure is explicitly needed.
- Forced manuscript figures to use fixed `[H]` placement so maps and covariate
  panels appear in source order as vertical figures rather than floating away
  from the surrounding methods text.
- Added a Discussion subsection comparing the proposed public-data Bayesian
  receptor-exposure pipeline with deterministic fire-danger scores, generic ML
  classifiers, proprietary powerline ignition/failure models, fire-spread
  simulators, and Bayesian decision models.

## Paper Boundary

Safe conclusion:

> A physics-informed Bayesian exposure pipeline using only public data can rank
> transmission-line segments by external wildfire exposure under temporal
> holdout. Compared with a deterministic calibrated physics score, Bayesian
> posterior ranking improves rare-event PR-AUC and top-decile capture. Compared
> with common tree-based ML baselines, the selected physics-informed linear core
> generalizes better in 2022-2023. The Bayesian contribution is posterior
> exceedance and posterior rank probabilities for extreme-disaster triage.

Avoid claiming:

- line-caused ignition prediction;
- equipment causal attribution;
- outage probability;
- full operational utility without private asset-condition data;
- LANDFIRE static fuel alone predicts exposure.

## Next Steps

1. Build manuscript-ready result tables from Phase 4-6.
2. Add Stan convergence diagnostics or a longer full MCMC run.
3. Draft methods text for exogenous exposure label construction.
4. Add spatial block holdout as an additional robustness check.

## 2026-07-07 Review Batch

New review response files are stored under:

```text
docs/revisions/20260707_112554/
```

Naming rule:

```text
NN_YYYYMMDD_HHMMSS_short-topic.md
```

Current decision: do not upload the 2026-07-06 PDF directly. The next work
should begin with P0 QA before further manuscript polishing:

1. Audit LANDFIRE unit decoding: `CH / 10`, `CBH / 10`, `CBD / 100`.
2. Audit whether `FBFM40` is treated as categorical rather than continuous.
3. Reframe the manuscript as retrospective annual exposure ranking under
   observed annual environmental conditions unless prospective predictors are
   rebuilt.
4. Verify whether M5 was pre-specified or selected after inspecting the
   2022-2023 holdout.
5. Add climatology baseline, Brier Skill Score, top-k capture curves, and
   dependence-aware uncertainty checks.
6. Make posterior top-decile rank probability the primary Bayesian output;
   treat posterior exceedance probability as secondary until probability
   calibration improves.

## 2026-07-07 Phase 9 Revision Completion

Revision batch:

```text
20260707_113214
```

New outputs:

```text
scripts/phase9_revision_qa_outputs.py
docs/revisions/20260707_113214/
outputs/tables/phase9_20260707_113214_landfire_unit_audit.csv
outputs/tables/phase9_20260707_113214_climatology_brier_skill.csv
outputs/tables/phase9_20260707_113214_topk_capture_curve.csv
outputs/tables/phase9_20260707_113214_bootstrap_metric_differences.csv
outputs/figures/phase9/
manuscript/main_20260707_113214_retrospective_qa.tex
manuscript/main_20260707_113214_retrospective_qa.pdf
manuscript/main.tex
manuscript/main.pdf
```

Manuscript framing is now:

- retrospective annual external wildfire exposure ranking under observed
  annual environmental conditions;
- transmission-line segments are receptor assets only;
- no ignition, failure, outage, damage, or legal-responsibility claim;
- Bayesian value is posterior top-decile rank probability and posterior
  exceedance probability, not broad point-prediction superiority.

Key quantitative results:

- 2022-2023 holdout rows: 22,510.
- Holdout positives: 356.
- Holdout prevalence: 1.5815%.
- Climatology Brier score: 0.015565.
- Brier skill scores are slightly negative for logistic L2, Bayesian Laplace,
  and deterministic calibrated probabilities. Do not claim calibration
  superiority.
- Top-10% row capture: Bayesian Laplace 28.93%, logistic L2 28.93%,
  deterministic calibrated 21.91%.
- Segment-cluster bootstrap suggests Bayesian Laplace exceeds deterministic on
  top-10% capture, but does not materially exceed logistic L2.

LANDFIRE audit:

- Processed CH and CBH values should be interpreted as raw / 10.
- Processed CBD values should be interpreted as raw / 100.
- FBFM40 is categorical and must not be treated as a continuous final feature.
- Selected Bayesian/L2 core does not include FBFM40, but Phase 5 M1/M3/M4
  exploratory ablations currently do; treat those ablations as diagnostic until
  categorical encoding or removal is implemented.
- Constant unit rescaling of CH/CBH/CBD does not change standardized linear
  selected-core fits, but it matters for physical interpretation, figure labels,
  and future non-linear/threshold modeling.

Remaining high-priority tasks:

1. Add formal bibliography and replace TODO citations.
2. Rebuild LANDFIRE covariate diagnostic figure with decoded unit labels.
3. Encode FBFM40 categorically or remove it from final ablations.
4. Run spatial block validation and buffer sensitivity.
5. Run time-matched LANDFIRE sensitivity.
6. Run full Stan diagnostics and posterior predictive checks.
