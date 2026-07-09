# Physics-Informed Bayesian Wildfire Exposure Pipeline for California

This project is a reproducible preprint workspace for estimating wildfire exposure
of California transmission-line segments under extreme-weather uncertainty.

Core decision outputs:

- `P(exposure > threshold | data)`
- `P(rank in top 10% | data)`
- posterior rank stability versus deterministic risk ranking

## Data Strategy

The first reproducible case study uses California / western US public data:

- transmission lines: HIFLD / ArcGIS Hub, filtered to California
- fire perimeters: CAL FIRE or MTBS
- active fires: NASA FIRMS MODIS/VIIRS
- meteorology: gridMET or ERA5
- fuel and vegetation: LANDFIRE / NLCD / ESA WorldCover
- topography: SRTM / USGS DEM

Large raster products are intentionally not bulk-downloaded until the target study
area and time window are fixed.

## Folder Layout

```text
data/raw/       downloaded source data, unchanged
data/interim/   clipped and harmonized working data
data/processed/ model-ready tables and rasters
scripts/        reproducible download and preprocessing scripts
notebooks/      analysis notebooks
docs/           data notes and method notes
outputs/        figures, tables, and manuscript outputs
```

## Initial Scope

Default case-study window:

- region: California
- period: 2017-2023
- spatial target: transmission-line segments
- decision unit: line segment or buffered line segment

## Core Project Notes

- [Project memory](PROJECT_MEMORY.md)
- [LaTeX manuscript draft](manuscript/main.tex)
- [Approved experiment design](docs/approved_experiment_design.md)
- [Data inventory](docs/data_inventory.md)
- [Public data sources](docs/data_sources.md)
- [Data and gap plan](docs/data_gap_plan.md)
- [Analysis framework](docs/analysis_framework.md)
- [CAL FIRE cause analysis](docs/calfire_cause_analysis.md)
- [Manuscript results summary](docs/manuscript_results_summary.md)
- [Phase 1 outputs](docs/phase1_outputs.md)
- [Phase 8 manuscript visuals script](scripts/phase8_manuscript_visuals.py)
- [Project merge note](docs/project_merge_note.md)
- [Execution roadmap](docs/roadmap.md)

## Research Boundary

Transmission lines are treated as externally exposed linear assets, not ignition
sources. The study estimates wildfire exposure ranking under uncertain weather,
fuel, and terrain conditions; it does not estimate powerline-caused ignition,
equipment failure, or outage probability.

The approved analysis unit is `segment-year` for 2017-2023, enabling
year-specific fire labels and fire-season weather/dryness summaries.
