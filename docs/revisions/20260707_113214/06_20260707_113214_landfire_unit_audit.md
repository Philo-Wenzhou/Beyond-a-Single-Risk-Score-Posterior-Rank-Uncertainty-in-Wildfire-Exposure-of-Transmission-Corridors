# LANDFIRE Unit and Support Audit

The processed table currently stores LF2024 canopy height/base-height/bulk-density
as raw raster-coded values rather than decoded physical units.

Key audit decisions:

- Canopy height should be reported after raw / 10.
- Canopy base height should be reported after raw / 10.
- Canopy bulk density should be reported after raw / 100.
- FBFM40 is categorical and should not be treated as a continuous predictor.

The selected Bayesian/L2 feature core does not include FBFM40, but Phase 5
M1/M3/M4 ablation models currently do. Those ablations should be treated as
diagnostic until FBFM40 is encoded categorically or removed.

The selected core uses z-scored CH, CBH, and CBD terms, so constant unit
rescaling would not change the linear standardized fit. It does change physical
interpretation, plotting labels, and any non-linear or threshold interpretation.
