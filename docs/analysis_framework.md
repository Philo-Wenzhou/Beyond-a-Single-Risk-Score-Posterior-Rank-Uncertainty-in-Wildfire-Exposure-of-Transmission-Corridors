# Analysis Framework

## Research Claim

A deterministic wildfire-risk score is not sufficient for infrastructure
decision support under extreme-weather uncertainty. A Bayesian exposure-ranking
pipeline can provide more useful decision metrics:

- posterior exceedance probability: `P(exposure > threshold | data)`;
- posterior rank probability: `P(rank in top 10% | data)`;
- rank-stability diagnostics under uncertain wind, fuel moisture, and spread
  model residuals.

## Causal Boundary

Transmission lines are modeled as externally exposed assets, not ignition
sources.

The target quantity is not:

```text
P(powerline causes fire)
P(line fails)
P(outage occurs)
```

The target quantity is:

```text
P(external wildfire exposure exceeds an actionable threshold for asset segment i)
```

## Modular System Design

```text
External wildfire environment
  weather, fuel, terrain, historical fire activity
        |
        v
Dynamic hazard module H_i(t)
        |
        v
Asset receptor interface
  line segment, road segment, community polygon, substation point
        |
        v
Static susceptibility module A_i
        |
        v
Bayesian exposure module p(X_i | D)
        |
        v
Decision metrics
  P(X_i > threshold), P(rank_i in top 10%), expected loss
```

## Analysis Unit

The approved analysis unit is `segment-year`:

```text
(i, t)
```

where `i` is a fixed-length transmission-line segment and `t` is a year from
2017 to 2023. This supports annual fire labels and fire-season weather/dryness
summaries.

## Segment-Year Exposure Definition

For each asset segment `i`:

```text
X_i(t) = A_i * H_i(t)
```

where:

- `A_i`: static susceptibility of the asset context;
- `H_i(t)`: dynamic external wildfire hazard;
- `X_i(t)`: exposure intensity, not failure probability.

The main Bayesian output is:

```text
q_i = P(X_i(t) > tau | D)
```

Rank stability is:

```text
rho_i = P(rank(X_i) <= K | D)
```

For top-decile decision support:

```text
K = ceil(0.10 * number_of_segments)
```

## Static Susceptibility Module

Candidate static predictors:

| Predictor | Source | Interpretation |
|---|---|---|
| fuel continuity near segment | LANDFIRE / land cover | whether fire can reach or surround the corridor |
| slope and aspect | DEM | terrain-driven spread tendency |
| historical burned-area frequency | CAL FIRE perimeters | repeated exposure context |
| distance to prior perimeters | CAL FIRE perimeters | historical proximity |
| voltage class | HIFLD | consequence weight, not failure probability |
| nearby buildings / WUI | optional | consequence or exposure context |

Static susceptibility can be implemented first as an interpretable weighted
index, then replaced with a calibrated model.

## Dynamic Hazard Module

Candidate dynamic predictors:

| Predictor | Source | Interpretation |
|---|---|---|
| wind speed | gridMET / ERA5 | spread and wind-stress environment |
| relative humidity | gridMET / ERA5 | fine-fuel drying |
| VPD | gridMET | atmospheric drying demand |
| temperature | gridMET / ERA5 | heat stress and drying |
| dead-fuel moisture proxy | gridMET / fire danger variables | ignition/spread readiness |
| ERC / BI | gridMET if used | fire-danger intensity proxy |
| active-fire density | FIRMS | nearby active fire pressure |

For the first paper, dynamic hazard can be computed on daily resolution, then
aggregated to high-risk days or fire-season windows.

## Deterministic Baseline

Build a transparent baseline:

```text
score_i = normalize(A_i) * normalize(H_i)
```

or:

```text
score_i = w1*fuel + w2*slope + w3*wind + w4*dryness + w5*history
```

This baseline is used only as the comparator. The paper should show where a
single score creates unstable or misleading rankings.

## Bayesian Exposure Model

The approved main model is a Bayesian segment-year external exposure model:

```text
y_exo_it ~ Bernoulli(p_it)

logit(p_it) =
  alpha
  + beta_1 * surface_fuel_hazard_i
  + beta_2 * fuel_continuity_i
  + beta_3 * dynamic_dryness_it
  + beta_4 * terrain_i
  + beta_5 * wind_it
  + beta_6 * fuel_continuity_i * dynamic_dryness_it
  + county_random_effect_i
  + year_random_effect_t
```

Core hypothesis:

```text
beta_6 > 0
```

meaning external exposure probability is highest where fuel continuity and
dynamic dryness are both high.

Monte Carlo uncertainty propagation remains useful for posterior decision
outputs:

1. sample wind uncertainty;
2. sample humidity / fuel-moisture uncertainty;
3. sample spread-emulator residual;
4. recompute segment exposure score;
5. repeat 1,000-5,000 times;
6. summarize posterior exceedance and rank probability.

Conceptual model:

```text
X_i^(s) = A_i^(s) * H_i^(s)
q_i = mean(X_i^(s) > tau)
rho_i = mean(rank(X_i^(s)) <= K)
```

where `s` indexes posterior / Monte Carlo draws.

## Model Ladder

| Model | Purpose |
|---|---|
| Model 0 | geometry / line attributes / county / year baseline |
| Model 1 | deterministic public baseline score |
| Model 2 | Bayesian external exposure model, main model |
| Model 3 | electrical-power-fire overlap diagnostic, optional |

Model 3 is not interpreted as calibrated powerline ignition probability.

## Cause-Specific Diagnostic

Electrical-power fires should be analyzed separately:

```text
electrical = 1 if CAUSE == 11
electrical = 0 for known non-electrical causes
```

Potential diagnostic:

```text
Pr(CAUSE = Electrical Power | fire occurred)
  = logit^-1(alpha + beta_wind * wind_percentile
                   + beta_vpd * VPD
                   + year effect
                   + region effect)
```

This is not the main paper target. It is a boundary check: if electrical-power
fires cluster under extreme wind, including them in receptor-exposure validation
would confound external exposure with asset-caused ignition.

## Main Experiments

### Experiment 1: Segment exposure labels

Create line segments and compare:

- `all_fire_exposure`;
- `exogenous_fire_exposure`;
- strict sensitivity excluding both `CAUSE = 11` and `CAUSE = 2`.

### Experiment 2: Deterministic versus Bayesian ranking

Compare:

- deterministic top 10%;
- posterior `P(rank in top 10%)`;
- posterior `P(exposure > threshold)`.

Key expected result:

```text
Some high deterministic scores are not robust under uncertainty, while some
moderate deterministic scores have high posterior exceedance probability.
```

### Experiment 3: Extreme-weather stress test

Condition the model on high-wind, low-humidity, high-VPD days and compare
ranking shifts.

### Experiment 4: Electrical-power cause diagnostic

Compare weather conditions on `CAUSE = 11` fires versus known non-electrical
fire causes. Use this to justify the exogenous-validation label.

### Experiment 5: Validation and ablation

Use:

- temporal holdout: train 2017-2021, test 2022-2023;
- spatial blocks or county leave-one-out;
- buffer sensitivity: 250 m, 500 m, 1000 m, 2000 m;
- ablation: geometry, terrain, weather, fuel structure, fuel continuity,
  dryness, and continuity by dryness interaction.

Report:

- ROC-AUC;
- PR-AUC;
- Brier score;
- calibration curve;
- top-decile capture rate.

## Minimum Publishable Figure Set

1. Study-area map: lines, fire perimeters, selected region.
2. Cause summary: distribution of CAL FIRE causes, with electrical-power fires highlighted.
3. Pipeline diagram: dynamic hazard, static susceptibility, Bayesian exposure, decision metrics.
4. Deterministic versus Bayesian ranking scatterplot.
5. Map of `P(exposure > threshold)`.
6. Map or bar chart of `P(rank in top 10%)`.

## Main Manuscript Positioning

Use the phrase:

```text
Bayesian decision-ready wildfire exposure ranking for externally exposed linear assets
```

Avoid framing as:

```text
powerline ignition prediction
equipment failure prediction
outage risk prediction
```
