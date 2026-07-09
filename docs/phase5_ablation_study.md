# Phase 5 Ablation Study

Goal: quantify which public-data modules improve external wildfire exposure
ranking for transmission-line receptor segments.

## Rebuild

```powershell
C:\anaconda3\python.exe scripts\phase5_ablation_study.py
```

The script reads:

```text
data/processed/phase3/segment_year_model_table.parquet
```

It does not call external network services.

## Model Ladder

All models use the same target:

```text
exogenous_fire_exposure
```

Training years:

```text
2017-2021
```

Temporal holdout:

```text
2022-2023
```

Models:

| ID | Meaning |
|---|---|
| M0 | geometry, voltage proxy, segment midpoint, DEM elevation |
| M1 | M0 + LANDFIRE fuel and canopy variables |
| M2 | M0 + gridMET annual weather and fire-danger variables |
| M3 | M0 + LANDFIRE + gridMET |
| M4 | M3 + all physics-informed interaction variables |
| M5 | selected physics core used by the Phase 4 decision model |

M5 is intentionally smaller than M4. It tests whether a selected
physics-informed feature set is more decision-useful than adding every
available public covariate.

## Outputs

Metrics:

```text
data/processed/phase5/phase5_ablation_metrics.csv
data/processed/phase5/phase5_ablation_metrics.parquet
```

Predictions:

```text
data/processed/phase5/phase5_ablation_predictions.parquet
```

Coefficients:

```text
data/processed/phase5/phase5_ablation_coefficients.csv
```

Report:

```text
outputs/tables/phase5_ablation_report.json
```

Figures:

```text
outputs/figures/phase5/phase5_ablation_validation_metrics.png
outputs/figures/phase5/phase5_ablation_brier_scores.png
```

## Current Results

Temporal holdout, 2022-2023:

| Model | ROC-AUC | PR-AUC | Brier | Row top-10% capture | Segment top-10% capture |
|---|---:|---:|---:|---:|---:|
| M0 | 0.489 | 0.024 | 0.016052 | 0.157 | 0.157 |
| M1 | 0.543 | 0.020 | 0.016076 | 0.149 | 0.149 |
| M2 | 0.665 | 0.029 | 0.015822 | 0.199 | 0.143 |
| M3 | 0.667 | 0.030 | 0.015821 | 0.222 | 0.152 |
| M4 | 0.671 | 0.030 | 0.015820 | 0.211 | 0.152 |
| M5 | 0.662 | 0.038 | 0.015723 | 0.289 | 0.219 |

## Interpretation

Stable conclusions:

- Dynamic weather and fire-danger variables are the largest source of ROC-AUC
  improvement.
- Adding every public covariate improves discrimination only modestly after
  gridMET is included.
- The selected physics core gives the strongest PR-AUC and top-decile capture,
  which is the more relevant decision metric for rare extreme-exposure events.

Important caveat:

- LANDFIRE alone is not sufficient in this temporal holdout. It is useful as a
  static receptor context, but the current evidence does not support claiming
  that static fuel layers alone produce strong annual exposure prediction.

Recommended manuscript wording:

```text
Public dynamic weather/fire-danger covariates drive most of the temporal
discrimination gain, while a selected physics-informed fuel-dryness feature set
improves rare-event top-decile capture relative to broader unselected feature
sets.
```

Avoid wording:

```text
LANDFIRE alone strongly predicts exposure.
```

## Recommended Python Load

```python
import pandas as pd

metrics = pd.read_parquet(
    r"E:\WPSDrive\198731884\WPS云盘\2026 申请\Bayesian_Wildfire_Exposure_CA\data\processed\phase5\phase5_ablation_metrics.parquet"
)

pred = pd.read_parquet(
    r"E:\WPSDrive\198731884\WPS云盘\2026 申请\Bayesian_Wildfire_Exposure_CA\data\processed\phase5\phase5_ablation_predictions.parquet"
)
```

## Relation to Phase 4

Phase 4 provides posterior decision metrics for the selected physics-core
model. Phase 5 explains why that selected model is used: it gives better
rare-event ranking and top-decile capture than broader but less targeted
feature sets.
