# Public Data Sources

## Recommended Minimum Reproducible Dataset

| Layer | Source | Planned role |
|---|---|---|
| Transmission lines | HIFLD Electric Power Transmission Lines / ArcGIS Hub | Linear infrastructure assets |
| Fire perimeters | CAL FIRE Fire Perimeters or MTBS | Burned-area validation labels |
| Active fires | NASA FIRMS MODIS/VIIRS | Ignition and active-fire evidence |
| Meteorology | gridMET; ERA5 as fallback | Extreme temperature, humidity, wind, VPD, fuel-moisture proxies |
| Fuel | LANDFIRE | Fire behavior fuel model / vegetation |
| Terrain | SRTM or USGS DEM | Slope, aspect, elevation |
| Land cover | NLCD or ESA WorldCover | Vegetation and exposure context |

## Download Policy

Raw files go under `data/raw/<source>/`.

Large rasters should be downloaded only after fixing:

- California subregion or bounding box
- years
- variables
- target resolution

This keeps the preprint project reproducible without making the workspace too
large to sync or review.

## Bayesian Pipeline Data Contract

Each final line segment should receive the following model-ready variables:

- `segment_id`
- `geometry`
- `line_voltage` or infrastructure class if available
- `fuel_class`
- `slope`
- `wind_speed`
- `temperature`
- `relative_humidity`
- `vpd`
- `dfmc_mean`
- `dfmc_sd`
- `spread_potential_mean`
- `spread_potential_sd`
- `historical_fire_exposure`
- `deterministic_risk`
- `posterior_exceedance_probability`
- `posterior_top10_probability`

