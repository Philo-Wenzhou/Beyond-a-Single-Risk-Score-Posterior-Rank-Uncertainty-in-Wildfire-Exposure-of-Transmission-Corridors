# Dependence and Uncertainty Audit

A preliminary paired bootstrap resampled segment IDs to account for repeated
segment-years. This is not a replacement for spatial block validation.

| comparison                           |   delta_pr_auc_mean |   delta_pr_auc_q025 |   delta_pr_auc_q975 |   delta_top10_capture_mean |   delta_top10_capture_q025 |   delta_top10_capture_q975 |   n_boot |
|:-------------------------------------|--------------------:|--------------------:|--------------------:|---------------------------:|---------------------------:|---------------------------:|---------:|
| Bayesian Laplace minus Deterministic |         0.0103227   |         0.00509525  |         0.0166085   |                0.0676676   |                 0.0188038  |                   0.119692 |      120 |
| Bayesian Laplace minus Logistic L2   |        -0.000176967 |        -0.000280035 |        -8.45723e-05 |               -0.000604936 |                -0.00611901 |                   0        |      120 |

Required follow-up validation:

- spatial block validation;
- year/block split sensitivity;
- buffer-radius sensitivity;
- time-matched LANDFIRE sensitivity;
- full Stan diagnostics and posterior predictive checks.
