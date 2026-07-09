You are performing the final submission-clean pass on:

- main_20260707_113214_retrospective_qa.tex
- references_wildfire_exposure_verified.bib
- REFERENCE_CITATION_MAP.md

Target: an EarthArXiv V1 preprint.

The manuscript is a retrospective, public-data, external-wildfire exposure-ranking study for transmission-line receptor assets. It is NOT an ignition, failure, outage, damage, or responsibility model.

ABSOLUTE RULES
1. Do not invent citations, DOIs, data versions, numerical results, model-selection history, or validation results.
2. Use only BibTeX keys present in references_wildfire_exposure_verified.bib.
3. Do not cite internal/private company work.
4. Do not change numeric model outputs unless a scripted output proves a transcription error.
5. Do not add CDD.
6. Preserve the retrospective interpretation: observed annual environmental conditions are associated with annual historical external exposure. Do not rewrite this as prospective forecasting.
7. If M5 pre-specification cannot be established from repository history or scripts, do not claim it was pre-specified.

TASK A — BIBLIOGRAPHY AND CITATIONS
1. Add:
   \usepackage[round,authoryear]{natbib}
   to the preamble.
2. Add before \end{document}:
   \bibliographystyle{plainnat}
   \bibliography{references_wildfire_exposure_verified}
3. Insert citations following REFERENCE_CITATION_MAP.md.
4. Remove the sentence:
   "Public-source citations are still marked as TODO placeholders until a bibliography is added."
5. Check that every \citep / \citet key exists in the supplied .bib file.
6. Compile through BibTeX and ensure no undefined citations or references remain.

TASK B — INTRODUCTION LITERATURE POSITIONING
Revise the Introduction into four compact paragraphs:
1. Western-US wildfire/fuel-aridity context and electricity-infrastructure exposure.
2. Explicit distinction between grid-to-fire ignition work and fire-to-grid infrastructure impact/exposure work.
3. Public-data constraint and why this study does not claim ignition/failure/outage probability.
4. Bayesian decision question: point ranking versus posterior uncertainty in top-decile membership.

Use Yao et al. (2022) as a contrast for electricity-infrastructure-induced wildfire prediction using ignition/wire-down and infrastructure data. Do NOT present Yao et al. as doing the same external-exposure target.
Use Dale et al. (2018) and Panossian & Elgindy (2023) for fire-to-grid/power-system impact context.

TASK C — FIGURE 4 FORMULA CONSISTENCY
The current Figure 4 image is mathematically inconsistent with Equations 10–12.
Regenerate or replace the workflow figure so its decision block uses EXACTLY:

q_i = P(\bar p_i > \tau | \mathcal D)

\rho_i = P(rank_\downarrow(\bar p_i) <= K | \mathcal D)

K = \lceil 0.1 N \rceil

Use rho_i, not r_i.
Use \bar p_i, not p_i.
State that rank is descending exposure rank.
The figure title/caption should say posterior exposure and posterior top-decile rank probabilities.
Do not leave old formula text embedded in the image.

TASK D — LANDFIRE DECODED FIGURES
The manuscript currently acknowledges that CH/CBH/CBD are raw raster-coded values in processed tables, but Appendix Figures 13–14 still label raw values as physical units.
Regenerate:
- phase2_landfire_preview.png
- phase3_covariate_qc_distributions.png
using:
  CH_m = CH_raw / 10
  CBH_m = CBH_raw / 10
  CBD_kg_m3 = CBD_raw / 100

Update units and axis labels.
If the source extraction script cannot be changed safely, generate decoded plotting columns at figure-generation time.
Do not alter selected-core standardized linear model results solely because of positive constant scaling; z(aX)=z(X) for a>0. However, confirm no threshold, clipping, nonlinear transform, or tree model uses the decoded variables before making any no-rerun claim.
FBFM40 is categorical. It must not be treated as a continuous physical magnitude in the selected Bayesian/L2 core.

TASK E — M5 / SELECTED CORE PROVENANCE
Search repository scripts, commit history if available, revision notes, and generated result files for how "M5 selected physics core" was chosen.

If there is explicit evidence it was specified before inspecting the 2022–2023 holdout:
- rename it consistently to "pre-specified physics-guided core"
- document the evidence in REVISION_SUMMARY.md
- state in Methods that it was fixed before holdout evaluation.

If there is no such evidence:
- do NOT call it pre-specified.
- rename it "physics-guided selected core".
- remove the sentence currently written like an internal reviewer note:
  "The current M5 selected core should also be described as a physics-guided selected core, not as an independently tuned final model unless pre-specification or nested model selection is documented."
- add one bounded sentence to Methods or Limitations:
  "Because feature-core selection was not evaluated with a nested temporal selection design, the 2022–2023 comparison should be interpreted as a retrospective model comparison rather than a locked final-test estimate."
Do not fabricate a validation split.

TASK F — DETERMINISTIC WEIGHT PROVENANCE
Audit the source of:
0.56 dryness + 0.30 fuel + 0.14 elevation.

Determine whether the weights are:
A. fixed heuristic weights,
B. fit using 2017–2021 training data, or
C. selected after inspecting holdout performance.

Then document the exact truth.

If A:
write:
"The weights were fixed as an a priori transparent heuristic comparator and were not optimized on the 2022–2023 holdout."
Add an equal-weight sensitivity only if a script can compute it without manual invention.

If B:
state the training-only fitting procedure exactly.

If C:
state that the comparator was selected retrospectively and do not describe the holdout comparison as locked final testing.

Do not leave the weight provenance unexplained.

TASK G — PROBABILITY BASELINE TERMINOLOGY
Audit Table 5 and Figure 6.

The value 0.015565 appears to use holdout prevalence:
pi_test = 356 / 22510 = 0.015815...

Do not call this simply "climatology baseline" if it uses pi_test.

Compute from existing data:
1. training prevalence pi_train
2. Brier score of constant p = pi_train on the 2022–2023 holdout
3. Brier score of the hindsight constant p = pi_test

Report them separately:
- Training-prevalence baseline: out-of-sample constant reference.
- Holdout-prevalence constant reference: best constant probability in hindsight.

Define Brier skill against the TRAINING-prevalence baseline as the primary BSS.
The holdout-prevalence reference may be shown as a calibration floor/reference but not as a deployable out-of-sample baseline.

Update Abstract, Equations 11 discussion, Figure 6, Table 5, Results, and Conclusion consistently.
If qi uses tau, define tau explicitly as pi_train.

TASK H — EXACT FEATURE-CONSTRUCTION TABLE
Add a booktabs table:
"Exact construction of model covariates"

Columns:
Variable | Source | Raw unit | Temporal aggregation | Spatial extraction | Role/sign in engineered index

Rows:
VPD
ERC
BI
wind
FM100
FM1000
RMIN
PR
elevation
canopy cover
canopy height
canopy bulk density

Read actual scripts to fill temporal aggregation and spatial extraction.
Do not infer from figure titles if code says otherwise.
Examples that must be confirmed from code:
- annual p95
- annual p05
- annual sum
- midpoint nearest cell
- raster sample
- buffer zonal mean

For CH and CBD report decoded units:
CH raw/10 m
CBD raw/100 kg m^-3

Do not include canopy base height in the selected fuel index if Equation 3 does not use it; list it only as a diagnostic covariate if that is the truth.

TASK I — STAN POSITIONING
Stan MCMC is not a separate predictive model family.
In Table 4 either:
1. rename the first column to "Model / inference", OR
2. move Stan MCMC pilot out of the main comparison table into a computational-sensitivity paragraph/table.

Preferred:
Keep Bayesian logistic (Laplace) in the main model comparison.
Move Stan pilot to a short sensitivity statement:
"An initial Stan run reproduced the Laplace point-ranking metrics; full convergence and posterior predictive diagnostics remain future work."

TASK J — FIGURE CLEANUP
1. Remove Figure 7 if Figure 8 contains the same posterior decision information more completely.
2. Keep Figure 8, enlarge it to a full-width page or landscape so titles/colorbars are readable.
3. Remove project-development language from all figure graphics and captions:
   - "Phase 3"
   - "Phase 4"
   - "preview"
   - "QC"
4. Replace with:
   - "covariate spatial distributions"
   - "covariate diagnostics"
   - "posterior decision metrics"
5. Rebuild Appendix figures after LANDFIRE decoding.
6. Check every figure/table is cited in text and figure numbering is sequential.

TASK K — SPATIAL VALIDATION CITATION AND WORDING
Cite Roberts et al. (2017), and optionally Valavi et al. (2019), when stating that temporal holdout is not a substitute for spatially blocked validation.
Do not imply spatial generalization has been established.

TASK L — FINAL SUBMISSION CLEAN
1. Replace date:
   July 7, 2026 revision
   with:
   July 2026
2. Remove all internal-review wording:
   - "current revision"
   - "current prototype" where not analytically necessary
   - "Phase 5"
   - "M5" from prose unless a model-table identifier is needed
   - "should also be described"
   - "required follow-up analysis" phrased as reviewer instruction
3. Preserve explicit limitations but write them as manuscript prose, not QA notes.
4. Run:
   pdflatex
   bibtex
   pdflatex
   pdflatex
5. Verify:
   - no TODO
   - no undefined citations
   - no undefined references
   - no duplicate figure labels
   - no figure formula mismatch
   - no raw LANDFIRE codes labeled as metres or kg m^-3
   - no "climatology" misuse
   - no unsupported pre-specification claim

OUTPUT
1. main_submission_clean.tex
2. main_submission_clean.pdf
3. references_wildfire_exposure_verified.bib
4. REVISION_SUMMARY.md
5. SUBMISSION_CHECKLIST.md

In REVISION_SUMMARY.md, explicitly report:
- M5/core selection provenance finding
- deterministic weight provenance finding
- pi_train and pi_test
- primary Brier baseline definition
- whether selected-core model outputs required rerunning after LANDFIRE decoding
- whether any ablation result using continuous FBFM40 remains in the manuscript
