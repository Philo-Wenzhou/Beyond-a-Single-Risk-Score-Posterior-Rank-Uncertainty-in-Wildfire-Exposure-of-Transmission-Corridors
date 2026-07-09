# Physics-Informed Bayesian Wildfire Exposure Pipeline for California

This repository contains a reproducible research workflow for estimating wildfire
exposure of transmission-line segments in California under uncertainty in weather,
fuel, and terrain conditions. The project combines public geospatial data,
probabilistic modeling, and decision-oriented outputs to support infrastructure
exposure assessment rather than ignition or outage prediction.

## Research objective

The workflow is designed to quantify how likely a transmission-line segment is to
experience high wildfire exposure under uncertain environmental conditions. The
main outputs are:

- posterior exceedance probabilities: `P(exposure > threshold | data)`
- posterior top-decile rank probabilities: `P(rank in top 10% | data)`
- rank-stability diagnostics relative to deterministic risk rankings

## Why this project matters

Transmission lines are treated as externally exposed linear assets, not ignition
sources. The analysis focuses on exposure ranking and uncertainty-aware decision
support for corridor segments, with a clear distinction from powerline-caused
ignition, equipment failure, or outage probability.

## Data and modeling strategy

The current implementation uses publicly available California and western-US data
sources, including:

- transmission lines: HIFLD / ArcGIS Hub
- fire perimeters: CAL FIRE / MTBS
- active fire detections: NASA FIRMS MODIS / VIIRS
- meteorology: gridMET / ERA5
- fuel and vegetation: LANDFIRE / NLCD / ESA WorldCover
- topography: SRTM / USGS DEM

The analysis is organized around a `segment-year` unit for 2017-2023, enabling
annual fire labels and fire-season summaries while keeping the workflow modular
and reproducible.

## Repository structure

```text
scripts/            reproducible preprocessing and analysis workflows
scripts_v2/         newer modeling and validation pipeline components
stan/               Stan model definitions
public_pipeline/    lighter-weight public-data demonstration workflow
docs/               method notes, analysis framework, and result summaries
data/               source and working geospatial data (not all products are versioned)
outputs/            figures, tables, and derived results
```

## Reproducibility and outputs

The repository includes scripts for data preparation, model-table construction,
Bayesian ranking, ablation analyses, figure generation, and manuscript-oriented
outputs. The public-facing pipeline is also packaged in `public_pipeline/` as a
lighter-weight, data-driven entry point for reproducibility.

## Research boundary

This project estimates wildfire exposure ranking under uncertain weather, fuel,
and terrain conditions. It does not estimate:

- powerline-caused ignition probability
- equipment failure probability
- outage probability
- legal liability or causal attribution

For further methodological detail, see the documentation in `docs/` and the
public pipeline notes in `public_pipeline/`.
