# Phase 6 Machine Learning and Stan MCMC Validation

Goal: add external validation layers around the approved external wildfire
exposure pipeline without changing the scientific target. Transmission lines
remain receptor assets; the label remains exogenous fire exposure.

Run:

```powershell
C:\anaconda3\python.exe scripts\phase6_ml_and_stan_validation.py
```

## Validation Design

- Training years: 2017-2021.
- Temporal holdout years: 2022-2023.
- Label: `exogenous_fire_exposure`.
- Feature set: selected physics core from Phase 4 and Phase 5.
- Comparators:
  - calibrated deterministic physics score;
  - Bayesian Laplace posterior predictive mean from Phase 4;
  - L2 logistic regression;
  - balanced random forest;
  - balanced extra trees;
  - histogram gradient boosting.

The machine-learning models test whether the observed ranking gain is merely a
function of using a flexible discriminative learner. The Bayesian model remains
the decision model because it produces posterior decision quantities, including
probability of exceeding a policy threshold and probability of ranking in the
top decile.

## Stan MCMC Scaffold

The phase writes a Stan model and a matching standardized data package:

```text
stan/exogenous_logistic_selected_core.stan
data/processed/phase6/stan_selected_core_data.json
data/processed/phase6/stan_selected_core_metadata.json
scripts/phase6_run_stan_mcmc.py
```

The Stan model is a weakly regularized Bayesian logistic model:

```text
y[n] ~ bernoulli_logit(alpha + X[n] * beta)
alpha ~ normal(0, 5)
beta[k] ~ normal(0, 2)
```

Generated quantities include `p_new`, the posterior predictive probability for
each 2022-2023 holdout row. These draws can be converted to:

- `P(exposure > threshold)` by averaging `p_new > threshold` over posterior
  draws;
- `P(rank in top 10%)` by ranking segment-level posterior draws and averaging
  the indicator that each segment enters the top decile.

If `cmdstanpy` and CmdStan are installed, run:

```powershell
C:\anaconda3\python.exe scripts\phase6_run_stan_mcmc.py
```

Current local CmdStan root:

```text
F:\Rprogram\WeiPHD\.cmdstan_local\cmdstan-2.38.0
```

The project runner points to this root automatically. The user-provided
`src\cmdstan` path is inside the CmdStan tree; `cmdstanpy` expects the root
directory containing `makefile` and `bin/stanc.exe`.

For a fast pilot run:

```powershell
C:\anaconda3\python.exe scripts\phase6_run_stan_mcmc.py --chains 2 --parallel-chains 2 --warmup 200 --sampling 200 --suffix pilot
```

If `cmdstanpy` fails while parsing CSV metadata because of local non-UTF-8
console comments, extract posterior predictions directly:

```powershell
C:\anaconda3\python.exe scripts\phase6_extract_stan_csv.py --suffix pilot
```

## Outputs

```text
data/processed/phase6/phase6_model_comparison_metrics.csv
data/processed/phase6/phase6_model_comparison_metrics.parquet
data/processed/phase6/phase6_ml_and_comparator_predictions.csv
data/processed/phase6/phase6_ml_and_comparator_predictions.parquet
data/processed/phase6/phase6_run_manifest.json
outputs/tables/phase6_ml_stan_validation_report.json
outputs/figures/phase6/phase6_model_comparison_metrics.png
outputs/figures/phase6/phase6_calibration_check.png
outputs/figures/phase6/phase6_stan_mcmc_decision_maps.png
```

## Current Temporal-Holdout Results

| Model | ROC-AUC | PR-AUC | Brier | Row top-10% capture | Segment top-10% capture |
|---|---:|---:|---:|---:|---:|
| ML logistic L2 | 0.663 | 0.039 | 0.015713 | 0.289 | 0.216 |
| Bayesian Laplace posterior mean | 0.662 | 0.038 | 0.015718 | 0.289 | 0.216 |
| Deterministic calibrated score | 0.651 | 0.028 | 0.015734 | 0.219 | 0.118 |
| Balanced extra trees | 0.617 | 0.022 | 0.056091 | 0.180 | 0.104 |
| Histogram gradient boosting | 0.553 | 0.019 | 0.016647 | 0.132 | 0.149 |
| Balanced random forest | 0.568 | 0.018 | 0.034539 | 0.107 | 0.152 |

## Stan Pilot MCMC Results

The pilot run completed with 2 chains, 200 warmup iterations per chain, and
200 sampling iterations per chain, giving 400 posterior draws. Because
`cmdstanpy` failed while decoding non-UTF-8 CSV metadata, posterior draws were
extracted directly from the Stan CSV `p_new[...]` columns.

| Stan MCMC pilot metric | Value |
|---|---:|
| Posterior draws | 400 |
| Test rows | 22,510 |
| Test positives | 356 |
| ROC-AUC | 0.662 |
| PR-AUC | 0.038 |
| Brier | 0.015710 |
| Row top-10% capture | 0.289 |
| Segment top-10% capture | 0.216 |

Pilot outputs:

```text
data/processed/phase6/stan_mcmc_pilot/phase6_stan_row_posterior_predictions.parquet
data/processed/phase6/stan_mcmc_pilot/phase6_stan_segment_posterior_decision_metrics.parquet
data/processed/phase6/stan_mcmc_pilot/phase6_stan_posterior_summary.json
```

Interpretation: the selected linear physics core generalizes better than the
tree-based ML baselines under 2022-2023 temporal holdout. The point prediction
from standard logistic regression is nearly identical to the Bayesian Laplace
posterior mean, but the Bayesian path remains preferable for decision support
because it yields posterior exceedance and posterior rank probabilities rather
than a single deterministic score.

## How to Use in the Paper

Phase 6 supports three validation claims:

1. The temporal holdout prevents random split leakage across repeated
   segment-years.
2. Machine-learning baselines show whether nonlinear prediction alone can beat
   the Bayesian decision model.
3. The Stan scaffold upgrades the current Laplace posterior to full MCMC
   sampling while preserving the same target, feature set, and holdout design.
