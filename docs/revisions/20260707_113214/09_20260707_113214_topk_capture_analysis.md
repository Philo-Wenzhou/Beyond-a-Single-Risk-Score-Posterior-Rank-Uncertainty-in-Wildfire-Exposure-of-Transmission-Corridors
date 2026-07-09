# Top-k Capture Analysis

The top-k curve compares the fraction of holdout positives captured when only
the highest-ranked 1, 2, 5, 10, 20, or 30 percent of rows are selected.

At the 10 percent budget:

| model_label      |   capture_rate |   selected_positive_rate |   lift_over_random |
|:-----------------|---------------:|-------------------------:|-------------------:|
| Deterministic    |       0.219101 |                0.0346513 |            2.19101 |
| Bayesian Laplace |       0.289326 |                0.0457574 |            2.89326 |
| Logistic L2      |       0.289326 |                0.0457574 |            2.89326 |

This supports a bounded decision claim: Bayesian Laplace and L2 logistic
concentrate positives similarly and both exceed the deterministic comparator in
this temporal holdout. It does not support a claim that Bayesian point
prediction dominates L2 logistic.
