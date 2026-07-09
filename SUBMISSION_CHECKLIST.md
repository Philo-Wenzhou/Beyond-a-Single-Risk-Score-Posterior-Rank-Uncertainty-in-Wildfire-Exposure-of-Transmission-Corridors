# Submission Checklist

Date: 2026-07-07

Target: EarthArXiv V1 preprint.

## Manuscript Scope

- [x] Retrospective interpretation preserved.
- [x] Transmission-line segments framed as receptor assets.
- [x] No ignition, failure, outage, damage, or responsibility claim.
- [x] Public-data constraint stated.
- [x] Electrical-power overlap retained only as a diagnostic.

## Citations

- [x] `natbib` added.
- [x] Bibliography added with `plainnat`.
- [x] All `\citep` keys are present in `references_wildfire_exposure_verified.bib`.
- [x] BibTeX completed with zero warnings.
- [x] No internal/private company work cited.

## Methods and Validation

- [x] Introduction rewritten into four compact literature-positioning paragraphs.
- [x] `y_exo` label equation retained with fire index.
- [x] Exact covariate-construction table added.
- [x] Exact Bayesian/L2 design vector `x_it` defined.
- [x] Composite-index redundancy stated; individual coefficients not interpreted.
- [x] Segment construction details restored from source script.
- [x] Deterministic weight provenance stated as fixed heuristic comparator.
- [x] Deterministic chain `r_det -> s_det -> p_det` fully specified.
- [x] ML baseline implementation table added with class handling and fixed parameters.
- [x] Selected feature-core provenance stated without pre-specification claim.
- [x] L2 logistic and Bayesian Gaussian-prior relationship stated.
- [x] Laplace approximation cited.
- [x] Stan MCMC positioned as computational sensitivity, not a separate model family.
- [x] Spatial validation limitation cited.
- [x] Segment-cluster bootstrap method and percentile interval interpretation added.

## Figures and Tables

- [x] Bayesian workflow formula block regenerated.
- [x] Bayesian workflow decision block simplified to avoid raw formula text in PNG.
- [x] LANDFIRE covariate figure regenerated with decoded CH/CBH/CBD units.
- [x] Covariate diagnostics regenerated with decoded canopy height.
- [x] Posterior maps split into full-region main figure and appendix zoom figure.
- [x] Posterior rank-uncertainty table added.
- [x] Appendix figure floats flushed before bibliography.
- [x] Environmental covariate diagnostics moved to appendix.
- [x] Figure captions use reader-facing language.
- [x] Tables use `booktabs`.

## Probability Baselines

- [x] `pi_train = 0.0350955` reported.
- [x] `pi_test = 0.0158152` reported.
- [x] Training-prevalence constant baseline used as primary Brier reference.
- [x] Holdout-prevalence constant reference described as hindsight-only.
- [x] Brier skill table updated accordingly.

## Final Compile Checks

- [x] `pdflatex main_submission_clean.tex`.
- [x] `bibtex main_submission_clean`.
- [x] `pdflatex main_submission_clean.tex`.
- [x] `pdflatex main_submission_clean.tex`.
- [x] No undefined citations in final log.
- [x] No undefined references in final log.
- [x] No duplicate figure labels detected by LaTeX.
- [x] No raw LANDFIRE CH/CBH/CBD values labeled as physical units in manuscript figures.

## Remaining Scientific Work for a Journal Version

- [ ] Spatial block validation.
- [ ] Buffer-radius sensitivity.
- [ ] Time-matched LANDFIRE sensitivity.
- [ ] Full Stan convergence diagnostics.
- [ ] Posterior predictive checks.
