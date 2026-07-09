# Manuscript Core Results

Temporal holdout is 2022-2023. The target is exogenous wildfire exposure.

## Main Model Comparison

| Model | Family | ROC-AUC | PR-AUC | Brier | Row top-10% capture | Segment top-10% capture |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Deterministic calibrated | Deterministic score | 0.651 | 0.028 | 0.015734 | 0.219 | 0.118 |
| Bayesian Laplace | Bayesian Laplace | 0.662 | 0.038 | 0.015718 | 0.289 | 0.216 |
| Stan MCMC pilot | Bayesian MCMC | 0.662 | 0.038 | 0.015710 | 0.289 | 0.216 |
| ML logistic L2 | Machine learning | 0.663 | 0.039 | 0.015713 | 0.289 | 0.216 |
| Balanced extra trees | Machine learning | 0.617 | 0.022 | 0.056091 | 0.180 | 0.104 |
| Histogram gradient boosting | Machine learning | 0.553 | 0.019 | 0.016647 | 0.132 | 0.149 |
| Balanced random forest | Machine learning | 0.568 | 0.018 | 0.034539 | 0.107 | 0.152 |

## Feature-Set Ablation

| Model | Family | ROC-AUC | PR-AUC | Brier | Row top-10% capture | Segment top-10% capture |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| M0 geometry + terrain | Bayesian Laplace ablation | 0.489 | 0.024 | 0.016052 | 0.157 | 0.157 |
| M1 + LANDFIRE fuel | Bayesian Laplace ablation | 0.543 | 0.020 | 0.016076 | 0.149 | 0.149 |
| M2 + gridMET weather | Bayesian Laplace ablation | 0.665 | 0.029 | 0.015822 | 0.199 | 0.143 |
| M3 fuel + weather | Bayesian Laplace ablation | 0.667 | 0.030 | 0.015821 | 0.222 | 0.152 |
| M4 physics interaction | Bayesian Laplace ablation | 0.671 | 0.030 | 0.015820 | 0.211 | 0.152 |
| M5 selected physics core | Bayesian Laplace ablation | 0.662 | 0.038 | 0.015723 | 0.289 | 0.219 |

## Interpretation

- Bayesian Laplace and Stan MCMC pilot agree closely, supporting the Laplace prototype.
- The calibrated deterministic score is weaker for rare-event PR-AUC and top-decile capture.
- Tree-based ML baselines do not outperform the selected physics-informed linear core under temporal holdout.
- The decision value of Bayesian modeling is posterior exceedance and posterior rank probability, not only point prediction.

## Caution

This is external exposure ranking for receptor assets. It is not line-caused ignition prediction, equipment failure prediction, or outage prediction.
