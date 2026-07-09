# Data Inventory

Last checked: 2026-06-30

## Downloaded Raw Data

| Dataset | Local path | Record count | Notes |
|---|---:|---:|---|
| CEC California Electric Transmission Lines | `data/raw/cec/california_electric_transmission_lines.geojson` | 6,839 features | Canonical transmission-line receptor layer. |
| HIFLD US Electric Power Transmission Lines, California bbox | `data/raw/hifld/electric_power_transmission_lines.geojson` | 5,810 features | Bbox-filtered to `-125,32,-113,43`; clip to California boundary during preprocessing. |
| CAL FIRE California Historic Fire Perimeters | `data/raw/calfire/california_historic_fire_perimeters_2017_2023.geojson` | 2,829 features | Years 2017-2023, for validation and historical exposure labels. |
| US Census TIGER county boundaries | `data/raw/census/tl_2024_us_county.zip` | all US counties | Use `STATEFP = 06` to derive California boundary. |

## Phase 1 Processed Outputs

| Output | Local path | Count | Notes |
|---|---:|---:|---|
| Study area | `data/processed/phase1/study_area_northern_sierra_southern_cascades.gpkg` | 1 polygon | Bbox: lon -123.2 to -119.0, lat 38.6 to 41.8. |
| 1 km segments | `data/processed/phase1/segments_1km.gpkg` | 11,255 segments | CEC lines clipped to study area and split at 1 km maximum length. |
| 1 km segment buffers | `data/processed/phase1/segment_buffers_1km.gpkg` | 11,255 buffers | Main validation buffer radius. |
| Segment-year labels | `data/processed/phase1/segment_year_labels_2017_2023.csv` | 78,785 rows | 11,255 segments x 7 years. |
| Label summary | `data/processed/phase1/segment_year_label_summary.csv` | 8 rows | Annual and total counts for four labels. |

Phase 1 label totals:

| Label | Positive segment-year rows |
|---|---:|
| `all_fire_exposure` | 3,187 |
| `exogenous_fire_exposure` | 2,331 |
| `strict_exogenous_fire_exposure` | 2,075 |
| `electrical_power_fire_overlap` | 885 |

## Deferred Large or Credentialed Data

| Dataset | Why deferred | Planned use |
|---|---|---|
| gridMET | Full multi-year rasters are large; download after choosing variables and subregion. | Extreme weather, VPD, wind, fire-weather covariates, dead-fuel-moisture proxies. |
| LANDFIRE | Fuel rasters are large and should be clipped. | Fire behavior fuel model and vegetation/fuel class. |
| NASA FIRMS MODIS/VIIRS | Bulk API access typically needs a FIRMS map key. | Active fire evidence and ignition proxy. |
| DEM / SRTM | Download after target subregion is fixed. | Slope, aspect, elevation. |

## Immediate Preprocessing Target

Create a model-ready segment-year table:

1. attach weather, fuel, and terrain covariates after raster downloads;
2. build deterministic baseline scores;
3. fit Bayesian external exposure model;
4. run temporal, spatial, buffer, and ablation validation.
