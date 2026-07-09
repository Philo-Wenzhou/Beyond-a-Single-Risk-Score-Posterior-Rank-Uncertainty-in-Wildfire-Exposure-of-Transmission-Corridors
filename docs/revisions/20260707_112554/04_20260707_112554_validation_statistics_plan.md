# Validation and Statistics Plan

## Objective

Separate the paper's central ranking claim from unverified probability,
forecasting, and independence assumptions.

## V1 Temporal Framing

Current annual gridMET features are annual extreme or aggregate summaries.
Therefore the safe V1 framing is:

```text
retrospective annual exposure ranking under observed environmental conditions
```

Do not frame current results as:

- pre-fire seasonal prediction;
- prospective screening;
- future wildfire risk forecasting.

If prospective screening is desired later, rebuild labels and predictors as:

```text
Jan-Apr predictors -> May-Nov exposure labels
```

## V2 Model Selection Leakage Check

Question:

```text
Was M5 selected before or after inspecting 2022-2023 holdout performance?
```

If pre-specified:

- state this explicitly in Methods;
- document the pre-specification source.

If selected after seeing holdout:

- treat 2022-2023 as model-selection-contaminated;
- rebuild split:

```text
2017-2019 train
2020-2021 validation / model selection
2022-2023 locked final test
```

or use rolling-origin validation.

## V3 Climatology Baseline and Brier Skill

Holdout facts:

```text
n_test = 22,510
y_positive = 356
pi_test = 0.01582
```

Compute and report:

```text
BS_climatology = pi * (1 - pi)
BSS = 1 - BS_model / BS_climatology
```

Interpretation to test:

```text
Ranking lift may be positive even if probability skill is non-positive.
```

Manuscript implication:

- make `rho_i = P(rank in top 10% | D)` primary;
- make `q_i = P(exposure probability exceeds threshold | D)` secondary.

## V4 Top-k Capture Curve

Add a curve for:

```text
k = 1%, 2%, 5%, 10%, 20%, 30%
```

Compare:

- deterministic calibrated score;
- ML logistic L2;
- Bayesian posterior mean.

Primary metrics:

- cumulative positive capture;
- lift over random selection.

This should replace at least one redundant model-comparison figure.

## V5 Dependence-Aware Uncertainty

Current likelihood treats segment-year rows as conditionally independent.
Known dependence sources:

- repeated years per segment;
- adjacent 1 km segments;
- overlapping buffers;
- large fires creating many positive rows.

Minimum near-term checks:

1. spatial-block clustered bootstrap for metric differences;
2. year-block sensitivity if feasible;
3. explicit warning that current posterior rank probabilities may be
   overconfident.

Longer-term Bayesian model:

```text
eta_it = alpha + x_it beta + u_block[i] + v_year[t]
u_block ~ Normal(0, sigma_block^2)
v_year ~ Normal(0, sigma_year^2)
```

## Required Output

Create after execution:

```text
08_20260707_112554_temporal_framing_audit.md
09_20260707_112554_m5_selection_audit.md
10_20260707_112554_climatology_brier_skill.md
11_20260707_112554_topk_capture_curve_analysis.md
12_20260707_112554_dependence_uncertainty_audit.md
```

