# Manuscript Reframe Plan

## Target Version

The next manuscript version should be labeled as a post-review working draft,
not an EarthArXiv-ready final PDF.

Suggested file names for the next manuscript outputs:

```text
manuscript/main_20260707_112554_retrospective_qa.tex
manuscript/main_20260707_112554_retrospective_qa.pdf
```

## Main Framing Change

Replace prospective language with retrospective annual exposure language.

Use:

- retrospective annual exposure ranking;
- observed annual environmental conditions;
- historical external wildfire exposure;
- screening-level prioritization;
- receptor-asset exposure ranking.

Remove or rewrite:

- before future fires are known;
- prospective screening;
- future wildfire risk;
- forecast;
- operational warning.

## Abstract Revision Direction

The abstract should say:

1. This is a retrospective public-data ranking framework.
2. The target is historical external wildfire exposure.
3. Transmission lines are receptor assets.
4. Annual weather summaries are observed annual covariates, not pre-fire
   forecasts.
5. The main Bayesian output is posterior top-decile rank probability.
6. Posterior exceedance probability is secondary until calibration improves.
7. Absolute probability calibration does not yet beat a climatology baseline.

## Introduction Revision Direction

The first page should be compressed into one clean logic chain:

```text
Public environmental data
  -> historical external fire exposure of line segments
  -> ranking concentration under rare events
  -> Bayesian posterior rank probability for priority-set uncertainty
```

Do not mix in internal business algorithms, ignition causality, outages, or
future operational forecasts.

## Figure Changes

Delete from the main manuscript:

- current Figure 1 research-advantage heatmap.

Reason: it reads as self-scoring rather than evidence.

Replace with either:

- no replacement in the main paper; or
- a neutral taxonomy table in the Introduction.

Move to Supplement:

- gridMET covariate layers;
- DEM covariate layers;
- LANDFIRE covariate layers;
- covariate histograms;
- spatial QC maps;
- full calibration plot;
- duplicate posterior maps.

Keep in main paper:

- study area;
- cause-screened labels;
- annual label counts;
- Bayesian workflow;
- temporal validation;
- top-k capture curve;
- ablation summary;
- posterior rank map;
- clustered bootstrap effect comparison, if computed.

## Mathematical Edits

Use an explicit fire-indexed label definition:

```latex
\mathcal{F}^{exo}_t = \{j: year_j=t,\ cause_j \ne 11\}
```

```latex
y^{exo}_{it} =
\mathbf{1}\left\{
\exists j \in \mathcal{F}^{exo}_t:
B_i \cap P_j \ne \varnothing
\right\}.
```

Define the indicator command:

```latex
\newcommand{\ind}{\mathbf{1}}
```

Unify likelihood notation:

```latex
\prod_{(i,t)\in D}
p_{it}^{y^{exo}_{it}}(1-p_{it})^{1-y^{exo}_{it}}
```

Fix workflow figure formulas:

```text
q_i = P(pbar_i > tau | D)
rho_i = P(rank_down(pbar_i) <= K | D)
K = ceil(0.1 N)
```

## New Methods Subsection

Add:

```text
Relation to L2-Regularized Logistic Regression
```

Core point:

```text
Gaussian priors imply a ridge/L2-regularized logistic MAP estimator. Therefore
the similar discrimination between Bayesian logistic and L2 logistic is
expected. The paper studies uncertainty propagation into rank decisions.
```

## Limitations Upgrade

Move these from soft limitations to explicit audit status:

- LANDFIRE CH/CBH/CBD unit decoding under audit.
- FBFM40 categorical handling under audit.
- Annual covariates support retrospective ranking only.
- M5 model-selection history must be verified.
- Segment-year independence may understate posterior uncertainty.
- Probability calibration has not yet shown positive Brier skill.

