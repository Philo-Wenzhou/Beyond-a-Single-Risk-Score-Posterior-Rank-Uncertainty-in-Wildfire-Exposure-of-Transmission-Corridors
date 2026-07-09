# Phase 3 Model Tables

Goal: build analysis-ready covariate tables for segment-level and
segment-year Bayesian wildfire exposure modeling.

## Rebuild

```powershell
C:\anaconda3\python.exe scripts\phase3_build_model_tables.py
```

The script reads only local Phase 1 and Phase 2 data. It does not call external
network services.

## Outputs

Static segment covariates:

```text
data/processed/phase3/segment_static_covariates.csv
data/processed/phase3/segment_static_covariates.parquet
```

Annual weather covariates:

```text
data/processed/phase3/segment_year_weather_covariates.csv
data/processed/phase3/segment_year_weather_covariates.parquet
```

Main model table:

```text
data/processed/phase3/segment_year_model_table.csv
data/processed/phase3/segment_year_model_table.parquet
```

Summary:

```text
outputs/tables/phase3_model_table_summary.json
```

Figures:

```text
outputs/figures/phase3/phase3_covariate_qc_distributions.png
outputs/figures/phase3/phase3_spatial_qc_maps.png
```

## Table Grain

The main model table is one row per `segment_id` and `year`.

```text
segments: 11,255
years: 2017-2023
rows: 78,785
columns: 45
```

## Labels

Primary modeling label:

```text
exogenous_fire_exposure
```

Sensitivity and diagnostic labels:

```text
all_fire_exposure
strict_exogenous_fire_exposure
electrical_power_fire_overlap
```

`largest_fire_name` and `dominant_cause` are expected to be missing in most
rows, because they are only populated when a segment-year intersects a fire
perimeter.

## Static Covariates

Segment midpoint:

```text
mid_lon
mid_lat
```

Terrain:

```text
dem_elevation_m
```

LANDFIRE LF2024:

```text
landfire_fbfm40
landfire_canopy_cover_pct
landfire_canopy_height_m
landfire_canopy_base_height_m
landfire_canopy_bulk_density
```

## Annual gridMET Covariates

Fuel moisture:

```text
gridmet_fm100_p05
gridmet_fm100_mean
gridmet_fm1000_p05
gridmet_fm1000_mean
```

Atmospheric dryness and fire danger:

```text
gridmet_vpd_p95
gridmet_vpd_mean
gridmet_erc_p95
gridmet_erc_mean
gridmet_bi_p95
gridmet_bi_mean
```

Wind, humidity, precipitation:

```text
gridmet_vs_p95
gridmet_vs_mean
gridmet_rmin_p05
gridmet_rmin_mean
gridmet_pr_sum
gridmet_pr_p95
```

## Recommended Python Load

```python
import pandas as pd

model = pd.read_parquet(
    r"E:\WPSDrive\198731884\WPS云盘\2026 申请\Bayesian_Wildfire_Exposure_CA\data\processed\phase3\segment_year_model_table.parquet"
)

y = model["exogenous_fire_exposure"]
X = model[
    [
        "gridmet_vpd_p95",
        "gridmet_erc_p95",
        "gridmet_fm100_p05",
        "gridmet_vs_p95",
        "gridmet_pr_sum",
        "dem_elevation_m",
        "landfire_fbfm40",
        "landfire_canopy_cover_pct",
    ]
]
```

## Current Data Quality Notes

- gridMET and LANDFIRE covariates have no missing values in the current model
  table.
- `dem_elevation_m` has a small nodata rate near water or domain boundaries.
- CSV is retained for portability; Parquet should be preferred for iterative
  modeling.
