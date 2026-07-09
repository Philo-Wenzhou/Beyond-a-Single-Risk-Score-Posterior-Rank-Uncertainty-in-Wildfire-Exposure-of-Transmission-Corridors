# Verified reference directory and insertion map

This file maps the verified BibTeX keys in `references_wildfire_exposure_verified.bib`
to the current manuscript. The reference set is intentionally compact: it is designed
for the EarthArXiv V1 manuscript, not as an exhaustive literature review.

## 1. Introduction: wildfire–power-grid problem and target boundary

### Paragraph 1: wildfire exposure and infrastructure screening
Use:
- `abatzoglouWilliams2016wildfire`
- `dale2018californiaGrid`
- `panossianElgindy2023wildfire`

Suggested wording:
> Wildfire activity in the western United States is strongly linked to fuel aridity and changing fire-weather conditions \citep{abatzoglouWilliams2016wildfire}. Wildfires also create direct and indirect risks for electricity infrastructure and grid operations \citep{dale2018californiaGrid,panossianElgindy2023wildfire}.

### Paragraph 2: grid-to-fire versus fire-to-grid
Use:
- `yao2022electricityWildfire` for grid-to-fire / ignition prediction using utility ignition, wire-down, and infrastructure data.
- `dale2018californiaGrid` for fire-to-grid impacts.
- `panossianElgindy2023wildfire` for the two-way wildfire–power-system interaction.

Suggested wording:
> Existing work addresses both grid-to-fire ignition risk and fire-to-grid infrastructure impacts. Electricity-infrastructure ignition models can rely on ignition, wire-down, and detailed asset data \citep{yao2022electricityWildfire}, whereas wildfire exposure and grid-impact studies address the consequences of fires for electricity systems \citep{dale2018californiaGrid,panossianElgindy2023wildfire}.

Do NOT cite Yao et al. as support for the present external-exposure target. Cite it as a contrast:
their target is electricity-infrastructure-induced wildfire risk.

### Paragraph 3: public-data constraint
Use:
- `yao2022electricityWildfire`
- `panossianElgindy2023wildfire`

The point is that detailed utility data can materially change the target and feature set.

### Discussion comparison with fire-spread simulators
Use:
- `sullivan2009spread`

Suggested wording:
> Physical and quasi-physical fire-spread models target propagation dynamics and require a different set of process and scenario assumptions \citep{sullivan2009spread}.

---

## 2. Study Area and Public Data

### Transmission lines
Use:
- `cecTransmissionLines`

Insert in Table 1 source or the paragraph immediately before Table 1:
`\citep{cecTransmissionLines}`

### CAL FIRE fire perimeters
Use:
- `calfireFirePerimeters`

Suggested wording:
> CAL FIRE FRAP maintains and distributes the historical California fire-perimeter dataset used to construct the annual overlap labels \citep{calfireFirePerimeters}.

### gridMET
Use:
- `abatzoglou2013gridmet`

Suggested wording:
> Daily meteorological covariates were obtained from gridMET, a gridded surface meteorological dataset developed for ecological applications and modelling \citep{abatzoglou2013gridmet}.

### LANDFIRE
Use:
- `rollins2009landfire`
- `landfire2024update`
- `landfireDictionary`

Suggested wording:
> Static fuel and canopy context was obtained from LANDFIRE \citep{rollins2009landfire}. The present prototype uses the LF2024 update \citep{landfire2024update}; product coding and decoded units follow LANDFIRE documentation \citep{landfireDictionary}.

The LF2024 temporal-mismatch limitation should cite `landfire2024update`, because LF2024 is a current update product rather than a time-matched historical layer.

### USGS 3DEP
Use:
- `usgs3dep`

Suggested wording:
> Terrain covariates were derived from USGS 3DEP elevation data \citep{usgs3dep}.

---

## 3. Feature Core

### VPD / fuel aridity interpretation
Use:
- `abatzoglouWilliams2016wildfire`

Suggested wording:
> The dryness index is a physics-guided summary of atmospheric drying demand, fire-danger indices, wind, dead-fuel moisture, humidity, and precipitation. VPD and related fuel-aridity metrics have established links to western-US fire activity \citep{abatzoglouWilliams2016wildfire}.

### ERC, BI and dead-fuel-moisture context
Use:
- `deeming1977nfdrs`
- `jolly2024nfdrs`

Suggested wording:
> ERC and BI are National Fire Danger Rating System quantities \citep{deeming1977nfdrs}; recent NFDRS modernization has also emphasized improved live- and dead-fuel-moisture calculations \citep{jolly2024nfdrs}.

Do NOT describe the engineered dryness index as an official NFDRS index. It is a study-specific standardized composite.

---

## 4. Bayesian and L2 Logistic Methods

### Weakly regularized logistic regression / priors
Use:
- `gelman2008weakPriors`

Suggested wording:
> Weakly informative regularization is commonly used to stabilize logistic regression coefficients \citep{gelman2008weakPriors}.

Important:
The current manuscript uses Gaussian priors, whereas Gelman et al. recommend Student-t/Cauchy defaults after specific predictor scaling. Therefore cite this paper for weakly informative prior design, not as if it were the exact prior used here.

### Laplace approximation
Use:
- `tierneyKadane1986laplace`

Insert after Equation 9:
> The Laplace approximation uses a local Gaussian approximation around the posterior mode \citep{tierneyKadane1986laplace}.

### Gaussian prior and L2 relation
This relation follows directly from the log Gaussian prior:
`-log p(beta) = const + ||beta||^2 / (2 sigma_beta^2)`.
A citation is optional. If one is used, cite `gelman2008weakPriors` only as background on regularized Bayesian logistic regression. The manuscript should retain its explicit derivation rather than outsource the argument to a citation.

---

## 5. Validation

### PR-AUC under rare class imbalance
Use:
- `saitoRehmsmeier2015pr`

Suggested wording:
> Because the holdout prevalence is 1.5815%, precision-recall performance is emphasized alongside ROC-AUC; PR curves are more informative than ROC curves for heavily imbalanced binary classification settings \citep{saitoRehmsmeier2015pr}.

### Brier score
Use:
- `brier1950verification`

Suggested wording:
> Probabilistic accuracy is summarized with the Brier score \citep{brier1950verification}.

### Spatial dependence and block validation limitation
Use:
- `roberts2017crossvalidation`
- optionally `valavi2019blockcv`

Suggested wording:
> Temporal holdout does not remove spatial dependence among neighboring segments. Blocked validation is recommended when spatial or hierarchical dependence structures are present \citep{roberts2017crossvalidation}; spatially separated folds can be operationalized with block-based procedures \citep{valavi2019blockcv}.

---

## 6. Recommended minimum citation placement by manuscript section

- Abstract: no citations.
- Introduction paragraph 1:
  `\citep{abatzoglouWilliams2016wildfire,dale2018californiaGrid}`
- Introduction paragraph 2:
  `\citep{yao2022electricityWildfire,panossianElgindy2023wildfire}`
- Introduction public-data paragraph:
  `\citep{yao2022electricityWildfire}`
- Table 1 / data-source paragraph:
  `\citep{cecTransmissionLines,calfireFirePerimeters,abatzoglou2013gridmet,rollins2009landfire,usgs3dep}`
- Feature Core after dryness-index motivation:
  `\citep{abatzoglouWilliams2016wildfire,deeming1977nfdrs,jolly2024nfdrs}`
- Feature Core LANDFIRE unit sentence:
  `\citep{landfireDictionary}`
- Bayesian methods:
  `\citep{gelman2008weakPriors,tierneyKadane1986laplace}`
- Validation PR-AUC sentence:
  `\citep{saitoRehmsmeier2015pr}`
- Validation Brier sentence:
  `\citep{brier1950verification}`
- Limitations spatial validation:
  `\citep{roberts2017crossvalidation,valavi2019blockcv}`
- Discussion fire-spread contrast:
  `\citep{sullivan2009spread}`
- Discussion grid-to-fire / fire-to-grid contrast:
  `\citep{yao2022electricityWildfire,dale2018californiaGrid,panossianElgindy2023wildfire}`

## 7. References intentionally NOT included

- CDD references: CDD should not enter V1.
- Generic deep-learning wildfire papers: they do not directly support the present target.
- Papers on power-line ignition optimization or PSPS are not necessary for the core V1 claim.
- News reports and utility press releases should not be used for scientific framing.
- Proprietary internal project documents should not be cited.

## 8. LaTeX integration

For the current `article` manuscript, add to the preamble:

```latex
\usepackage[round,authoryear]{natbib}
```

Before `\end{document}`, after the appendices:

```latex
\bibliographystyle{plainnat}
\bibliography{references_wildfire_exposure_verified}
```

Compile with:

```text
pdflatex main_20260707_113214_retrospective_qa.tex
bibtex main_20260707_113214_retrospective_qa
pdflatex main_20260707_113214_retrospective_qa.tex
pdflatex main_20260707_113214_retrospective_qa.tex
```

Do not add citations to every sentence. Use citations at the claim, data-source, or method-definition level.
