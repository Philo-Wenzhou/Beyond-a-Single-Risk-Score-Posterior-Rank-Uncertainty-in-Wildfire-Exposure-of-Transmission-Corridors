# Phase 4 Bayesian Ranking Prototype

Goal: compare a deterministic public physics score against Bayesian posterior
decision metrics for external wildfire exposure ranking.

## Rebuild

```powershell
C:\anaconda3\python.exe scripts\phase4_bayesian_ranking.py
```

The script reads:

```text
data/processed/phase3/segment_year_model_table.parquet
```

It writes all outputs under:

```text
data/processed/phase4/
outputs/tables/
outputs/figures/phase4/
```

## Model

Current prototype:

```text
y_exogenous_it ~ Bernoulli(p_it)
logit(p_it) = alpha + X_it beta
```

The Bayesian posterior is approximated with a Laplace approximation around a
weakly regularized logistic MAP estimate. This is a reproducible local
prototype because PyMC/CmdStan are not available in the current environment.

Training years:

```text
2017-2021
```

Temporal holdout:

```text
2022-2023
```

Posterior draws:

```text
1500
```

## Decision Quantities

Threshold:

```text
tau = training prevalence of exogenous_fire_exposure = 0.0350955
```

Segment-level posterior quantities:

```text
posterior_mean_exposure_prob
posterior_sd_exposure_prob
p_exposure_gt_threshold
p_rank_top10
```

Top-decile definition:

```text
K = ceil(0.10 * 11255) = 1126 segments
```

## Outputs

Segment decision metrics:

```text
data/processed/phase4/phase4_segment_posterior_decision_metrics.csv
data/processed/phase4/phase4_segment_posterior_decision_metrics.parquet
```

Segment-year predictions:

```text
data/processed/phase4/phase4_segment_year_predictions.csv
data/processed/phase4/phase4_segment_year_predictions.parquet
```

Model coefficients:

```text
data/processed/phase4/phase4_laplace_logit_coefficients.csv
data/processed/phase4/phase4_deterministic_calibration_coefficients.csv
```

Report:

```text
outputs/tables/phase4_bayesian_ranking_report.json
```

Figures:

```text
outputs/figures/phase4/phase4_temporal_holdout_validation.png
outputs/figures/phase4/phase4_deterministic_vs_bayesian_ranking.png
outputs/figures/phase4/phase4_decision_metric_maps.png
```

## Current Temporal Holdout Results

2022-2023 holdout:

| Metric | Deterministic | Bayesian |
|---|---:|---:|
| ROC-AUC | 0.651 | 0.662 |
| PR-AUC | 0.028 | 0.038 |
| Top-10% capture | 0.219 | 0.289 |
| Brier score | 0.015734 | 0.015718 |

The Brier comparison uses deterministic probabilities calibrated on the
training years. Ranking metrics use the deterministic physics score directly.

## Recommended Python Load

```python
import pandas as pd

segments = pd.read_parquet(
    r"E:\WPSDrive\198731884\WPS云盘\2026 申请\Bayesian_Wildfire_Exposure_CA\data\processed\phase4\phase4_segment_posterior_decision_metrics.parquet"
)

decision = segments[
    [
        "segment_id",
        "posterior_mean_exposure_prob",
        "p_exposure_gt_threshold",
        "p_rank_top10",
        "deterministic_segment_score",
        "observed_exogenous_exposure_years",
    ]
]
```

## Interpretation Boundary

These outputs estimate external wildfire exposure ranking for transmission
line receptor segments. They are not estimates of:

```text
P(powerline causes fire)
P(equipment failure)
P(outage)
```

The current prototype is appropriate for establishing the reproducible
decision-metric workflow. A later manuscript-grade model should replace the
Laplace approximation with a full hierarchical Bayesian model if the runtime is
available.
