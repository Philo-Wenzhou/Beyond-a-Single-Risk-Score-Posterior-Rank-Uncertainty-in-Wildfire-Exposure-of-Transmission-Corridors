# Phase 2 Data Preparation

Goal: pre-download, crop, validate, and preview all repeatedly used public data
needed for fuel/weather/terrain covariates.

## Runtime

Runtime used:

```text
C:\anaconda3\python.exe + project-local .python_deps
```

`env1` has useful geospatial packages but currently fails to import NumPy due to
a DLL issue when launched from this workspace. The active Phase 2 scripts
therefore inject the project-local `.python_deps` path before imports.

The active runtime has:

- geopandas
- rasterio
- rioxarray
- xarray
- netCDF4
- shapely
- pyogrio
- pyproj

## gridMET

Variables:

```text
fm100, fm1000, vpd, erc, bi, vs, rmin, pr
```

Years:

```text
2017-2023
```

Workflow:

1. download annual CONUS NetCDF files into `data/raw/gridmet/`;
2. crop each variable-year file to the study area;
3. save cropped NetCDF files into `data/interim/gridmet_study_area/`;
4. generate preview figures in `outputs/figures/data_previews/`.

Run foreground:

```powershell
C:\anaconda3\python.exe scripts\phase2_download_gridmet.py
```

Run background:

```powershell
.\scripts\phase2_run_gridmet_background.ps1
```

Preview after download:

```powershell
C:\anaconda3\python.exe scripts\phase2_preview_gridmet.py
```

Current status:

```text
56 / 56 annual CONUS NetCDF files downloaded.
56 / 56 study-area NetCDF subsets created.
```

Preview:

```text
outputs/figures/data_previews/phase2_gridmet_preview_2021.png
```

## DEM

Source:

```text
USGS 3DEP ImageServer exportImage
https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage
```

Workflow:

```text
download raw -> crop to study area -> validate -> preview
```

Run:

```powershell
C:\anaconda3\python.exe scripts\phase2_download_dem.py
C:\anaconda3\python.exe scripts\phase2_preview_dem.py
```

Current status:

```text
data/raw/dem_3dep/usgs_3dep_dem_study_area_2048.tif exists, 13.0 MB.
```

Preview:

```text
outputs/figures/data_previews/phase2_dem_preview.png
```

## LANDFIRE

LANDFIRE Product Service was probed and documented from the official LFPS app.
The service description states that LFPS takes a list of layers and an area of
interest and returns a multi-band GeoTIFF. The API docs expose:

```text
GET  /api/products
POST /api/job/submit
GET  /api/job/status
```

Validated current product layers:

```text
LF2024_FBFM40  40 Scott and Burgan Fire Behavior Fuel Models
LF2024_CC      Forest Canopy Cover
LF2024_CH      Forest Canopy Height
LF2024_CBH     Forest Canopy Base Height
LF2024_CBD     Forest Canopy Bulk Density
```

Saved API evidence:

```text
data/raw/landfire/lfps_home.html
data/raw/landfire/lfps_api_docs.html
data/raw/landfire/lfps_products.json
outputs/tables/landfire_lfps_probe.json
outputs/tables/landfire_lfps_job_manifest.json
```

Create a dry-run request manifest:

```powershell
C:\anaconda3\python.exe scripts\phase2_landfire_lfps_job.py
```

Submit and poll an LFPS job after setting a real requester email:

```powershell
$env:LANDFIRE_EMAIL="your.email@example.com"
C:\anaconda3\python.exe scripts\phase2_landfire_lfps_job.py --submit --poll
```

Current status:

```text
LFPS job c14949be-8e10-4ec7-959e-a3b6f5a51adb succeeded.
The requester email is redacted in the local manifest.
```

Downloaded output:

```text
data/raw/landfire/j85c0d8ece33b4407894b7ceea9c2aac1.zip
```

Extracted GeoTIFF:

```text
data/interim/landfire_study_area/j85c0d8ece33b4407894b7ceea9c2aac1/j85c0d8ece33b4407894b7ceea9c2aac1.tif
```

Preview:

```text
outputs/figures/data_previews/phase2_landfire_preview.png
```

The LFPS output is a 5-band GeoTIFF in EPSG:5070 at 90 m resolution. The bands
follow the request order: FBFM40, canopy cover, canopy height, canopy base
height, canopy bulk density.

## Status Check

```powershell
C:\anaconda3\python.exe scripts\phase2_status.py
```
