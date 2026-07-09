import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import xarray as xr

from phase2_data_config import DIRS, GRIDMET_VARIABLES, YEARS, ensure_phase2_dirs


PHASE1 = PROJECT / "data/processed/phase1"
PHASE3 = PROJECT / "data/processed/phase3"
FIG_DIR = PROJECT / "outputs/figures/phase3"
TABLE_DIR = PROJECT / "outputs/tables"

COLORS = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "grid": "#d8d5cd",
    "accent": "#005f73",
    "compare": "#c27a15",
}

GRIDMET_AGGREGATIONS = {
    "fm100": {"p05": 0.05, "mean": "mean"},
    "fm1000": {"p05": 0.05, "mean": "mean"},
    "vpd": {"p95": 0.95, "mean": "mean"},
    "erc": {"p95": 0.95, "mean": "mean"},
    "bi": {"p95": 0.95, "mean": "mean"},
    "vs": {"p95": 0.95, "mean": "mean"},
    "rmin": {"p05": 0.05, "mean": "mean"},
    "pr": {"sum": "sum", "p95": 0.95},
}

LANDFIRE_BANDS = {
    1: "landfire_fbfm40",
    2: "landfire_canopy_cover_pct",
    3: "landfire_canopy_height_m",
    4: "landfire_canopy_base_height_m",
    5: "landfire_canopy_bulk_density",
}


def ensure_dirs():
    ensure_phase2_dirs()
    PHASE3.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def segment_midpoints():
    segments = gpd.read_file(PHASE1 / "segments_1km.gpkg")
    if segments.crs is None:
        segments = segments.set_crs("EPSG:4326")
    metric = segments.to_crs("EPSG:3310")
    midpoint_geom = metric.geometry.interpolate(0.5, normalized=True)
    midpoint_metric = gpd.GeoDataFrame(
        segments.drop(columns="geometry").copy(),
        geometry=midpoint_geom,
        crs=metric.crs,
    )
    midpoint_wgs = midpoint_metric.to_crs("EPSG:4326")
    out = pd.DataFrame(
        {
            "segment_id": segments["segment_id"].astype(str),
            "mid_lon": midpoint_wgs.geometry.x,
            "mid_lat": midpoint_wgs.geometry.y,
        }
    )
    return segments, midpoint_wgs, out


def clean_sample(values, nodata):
    arr = np.array(values, dtype="float64")
    if nodata is not None:
        arr[arr == nodata] = np.nan
    arr[np.isinf(arr)] = np.nan
    return arr


def sample_raster_at_points(path: Path, points: gpd.GeoDataFrame, band_names: dict[int, str]):
    with rasterio.open(path) as src:
        pts = points.to_crs(src.crs)
        coords = [(geom.x, geom.y) for geom in pts.geometry]
        samples = np.array(list(src.sample(coords)), dtype="float64")
        nodata = src.nodata
    rows = {}
    for band_index, name in band_names.items():
        rows[name] = clean_sample(samples[:, band_index - 1], nodata)
    return pd.DataFrame(rows)


def find_landfire_tif():
    manifest = TABLE_DIR / "landfire_lfps_output_manifest.json"
    if manifest.exists():
        with manifest.open(encoding="utf-8") as handle:
            tif = Path(json.load(handle)["tif"])
        if tif.exists():
            return tif
    matches = sorted(DIRS["interim_landfire"].glob("**/*.tif"))
    if not matches:
        raise FileNotFoundError("No extracted LANDFIRE GeoTIFF found.")
    return matches[-1]


def build_static_covariates(points: gpd.GeoDataFrame, midpoint_df: pd.DataFrame):
    dem = DIRS["raw_dem"] / "usgs_3dep_dem_study_area_2048.tif"
    landfire = find_landfire_tif()
    static = midpoint_df.copy()
    static["dem_elevation_m"] = sample_raster_at_points(dem, points, {1: "dem_elevation_m"})["dem_elevation_m"]
    landfire_samples = sample_raster_at_points(landfire, points, LANDFIRE_BANDS)
    static = pd.concat([static, landfire_samples], axis=1)
    return static


def load_dataset_ascii(path: Path):
    with tempfile.TemporaryDirectory(prefix="phase3_gridmet_ascii_") as tmpdir:
        tmp_path = Path(tmpdir) / path.name
        shutil.copy2(path, tmp_path)
        with xr.open_dataset(tmp_path) as ds:
            return ds.load()


def pick_gridmet_var(ds):
    for name in ds.data_vars:
        if name not in {"crs", "day"}:
            return name
    return list(ds.data_vars)[0]


def nearest_indices(values, targets):
    vals = np.asarray(values)
    targets = np.asarray(targets)
    order = np.argsort(vals)
    sorted_vals = vals[order]
    pos = np.searchsorted(sorted_vals, targets)
    pos = np.clip(pos, 1, len(sorted_vals) - 1)
    left = sorted_vals[pos - 1]
    right = sorted_vals[pos]
    choose_left = np.abs(targets - left) <= np.abs(targets - right)
    nearest_sorted = np.where(choose_left, pos - 1, pos)
    return order[nearest_sorted]


def aggregate_da(da, spec):
    time_dim = "day" if "day" in da.dims else "time" if "time" in da.dims else None
    if time_dim is None:
        return da
    if isinstance(spec, float):
        return da.quantile(spec, dim=time_dim, skipna=True)
    if spec == "mean":
        return da.mean(dim=time_dim, skipna=True)
    if spec == "sum":
        return da.sum(dim=time_dim, skipna=True)
    raise ValueError(spec)


def build_weather_covariates(midpoint_df: pd.DataFrame):
    base = midpoint_df[["segment_id", "mid_lon", "mid_lat"]].copy()
    lons = base["mid_lon"].to_numpy()
    lats = base["mid_lat"].to_numpy()
    year_frames = []
    for year in YEARS:
        frame = base[["segment_id"]].copy()
        frame["year"] = year
        for var in GRIDMET_VARIABLES:
            path = DIRS["interim_gridmet"] / f"{var}_{year}_study_area.nc"
            ds = load_dataset_ascii(path)
            data_var = pick_gridmet_var(ds)
            da = ds[data_var]
            lon_name = "lon" if "lon" in da.coords else "longitude"
            lat_name = "lat" if "lat" in da.coords else "latitude"
            lon_idx = nearest_indices(da[lon_name].values, lons)
            lat_idx = nearest_indices(da[lat_name].values, lats)
            for suffix, spec in GRIDMET_AGGREGATIONS[var].items():
                img = aggregate_da(da, spec)
                values = img.values[lat_idx, lon_idx]
                frame[f"gridmet_{var}_{suffix}"] = values.astype("float64")
            ds.close()
        year_frames.append(frame)
        print(f"[weather] {year}")
    return pd.concat(year_frames, ignore_index=True)


def write_outputs(static, weather):
    labels = pd.read_csv(PHASE1 / "segment_year_labels_2017_2023.csv")
    model = labels.merge(static, on="segment_id", how="left").merge(weather, on=["segment_id", "year"], how="left")
    static_path = PHASE3 / "segment_static_covariates.csv"
    weather_path = PHASE3 / "segment_year_weather_covariates.csv"
    model_path = PHASE3 / "segment_year_model_table.csv"
    static.to_csv(static_path, index=False)
    weather.to_csv(weather_path, index=False)
    model.to_csv(model_path, index=False)
    static_parquet = PHASE3 / "segment_static_covariates.parquet"
    weather_parquet = PHASE3 / "segment_year_weather_covariates.parquet"
    model_parquet = PHASE3 / "segment_year_model_table.parquet"
    static.to_parquet(static_parquet, index=False)
    weather.to_parquet(weather_parquet, index=False)
    model.to_parquet(model_parquet, index=False)
    summary = {
        "static_rows": int(len(static)),
        "weather_rows": int(len(weather)),
        "model_rows": int(len(model)),
        "segments": int(static["segment_id"].nunique()),
        "years": YEARS,
        "label_columns": [
            "all_fire_exposure",
            "exogenous_fire_exposure",
            "strict_exogenous_fire_exposure",
            "electrical_power_fire_overlap",
        ],
        "static_columns": [col for col in static.columns if col != "segment_id"],
        "weather_columns": [col for col in weather.columns if col not in {"segment_id", "year"}],
        "outputs": {
            "static": str(static_path),
            "weather": str(weather_path),
            "model": str(model_path),
            "static_parquet": str(static_parquet),
            "weather_parquet": str(weather_parquet),
            "model_parquet": str(model_parquet),
        },
    }
    summary_path = TABLE_DIR / "phase3_model_table_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return model, summary


def style_ax(ax):
    ax.set_facecolor(COLORS["paper"])
    ax.grid(True, color=COLORS["grid"], linewidth=0.45, alpha=0.7)
    ax.tick_params(labelsize=7, colors=COLORS["axis"], length=2.5, width=0.5)
    for spine in ax.spines.values():
        spine.set_color("#4f565c")
        spine.set_linewidth(0.55)


def make_qc_figures(model):
    plot_model = model.copy()
    if "landfire_canopy_height_m" in plot_model:
        plot_model["landfire_canopy_height_decoded_m"] = plot_model["landfire_canopy_height_m"] / 10.0
    if "landfire_canopy_base_height_m" in plot_model:
        plot_model["landfire_canopy_base_height_decoded_m"] = plot_model["landfire_canopy_base_height_m"] / 10.0
    if "landfire_canopy_bulk_density" in plot_model:
        plot_model["landfire_canopy_bulk_density_decoded"] = plot_model["landfire_canopy_bulk_density"] / 100.0
    fig, axes = plt.subplots(2, 3, figsize=(10.2, 6.4), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    plot_specs = [
        ("dem_elevation_m", "Elevation at segment midpoint", "Elevation (m)"),
        ("landfire_canopy_cover_pct", "LANDFIRE canopy cover", "Percent"),
        ("landfire_canopy_height_decoded_m", "LANDFIRE canopy height", "Decoded metres (raw / 10)"),
        ("gridmet_vpd_p95", "Annual p95 VPD", "VPD"),
        ("gridmet_erc_p95", "Annual p95 ERC", "ERC"),
        ("gridmet_pr_sum", "Annual precipitation sum", "Precipitation"),
    ]
    for ax, (col, title, xlabel) in zip(axes.ravel(), plot_specs):
        vals = plot_model[col].replace([np.inf, -np.inf], np.nan).dropna()
        ax.hist(vals, bins=42, color=COLORS["accent"], alpha=0.84, edgecolor="white", linewidth=0.25)
        ax.set_title(title, fontsize=9, color=COLORS["text"], pad=7)
        ax.set_xlabel(xlabel, fontsize=7.5, color=COLORS["axis"])
        ax.set_ylabel("Rows", fontsize=7.5, color=COLORS["axis"])
        style_ax(ax)
    fig.suptitle("Covariate extraction diagnostics", fontsize=11, color=COLORS["text"], y=0.985)
    fig.text(
        0.5,
        0.018,
        "Rows are segment-year observations after merging exposure labels with static and annual covariates.",
        ha="center",
        va="bottom",
        fontsize=7.2,
        color=COLORS["axis"],
    )
    fig.subplots_adjust(left=0.07, right=0.985, top=0.91, bottom=0.11, wspace=0.28, hspace=0.38)
    out = FIG_DIR / "phase3_covariate_qc_distributions.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def make_spatial_qc_figure(model):
    segments = gpd.read_file(PHASE1 / "segments_1km.gpkg")
    if segments.crs is None:
        segments = segments.set_crs("EPSG:4326")
    segments = segments.to_crs("EPSG:3310")
    static_cols = [
        "segment_id",
        "dem_elevation_m",
        "landfire_canopy_cover_pct",
    ]
    static = model[static_cols].drop_duplicates("segment_id")
    weather_2021 = model.loc[
        model["year"] == 2021,
        ["segment_id", "gridmet_vpd_p95"],
    ]
    exposure = (
        model.groupby("segment_id", as_index=False)["exogenous_fire_exposure"]
        .sum()
        .rename(columns={"exogenous_fire_exposure": "exogenous_exposure_years"})
    )
    gdf = segments.merge(static, on="segment_id", how="left").merge(weather_2021, on="segment_id", how="left").merge(
        exposure, on="segment_id", how="left"
    )
    fig, axes = plt.subplots(2, 2, figsize=(8.8, 8.4), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    specs = [
        ("dem_elevation_m", "Elevation", "Elevation (m)", "cividis"),
        ("landfire_canopy_cover_pct", "Canopy cover", "Percent", "cividis"),
        ("gridmet_vpd_p95", "2021 p95 VPD", "VPD", "cividis"),
        ("exogenous_exposure_years", "Exogenous exposure count", "Years", "YlGnBu"),
    ]
    for ax, (col, title, cbar_label, cmap) in zip(axes.ravel(), specs):
        if col == "exogenous_exposure_years":
            gdf.plot(ax=ax, color="#d9d6ce", linewidth=0.22, alpha=0.62)
            positive = gdf[gdf[col] > 0]
            positive.plot(
                ax=ax,
                column=col,
                cmap="YlGnBu",
                linewidth=0.72,
                alpha=0.96,
                legend=True,
                legend_kwds={"label": cbar_label, "shrink": 0.72},
            )
        else:
            gdf.plot(
                ax=ax,
                column=col,
                cmap=cmap,
                linewidth=0.34,
                alpha=0.92,
                legend=True,
                legend_kwds={"label": cbar_label, "shrink": 0.72},
                missing_kwds={"color": "#c9c5ba", "linewidth": 0.25},
            )
        ax.set_title(title, fontsize=9.2, color=COLORS["text"], pad=7)
        ax.set_axis_off()
        ax.set_facecolor(COLORS["paper"])
    fig.suptitle("Spatial distributions of extracted segment covariates", fontsize=11, color=COLORS["text"], y=0.984)
    fig.text(
        0.5,
        0.018,
        "All panels use the same 1 km CEC transmission-line segments; weather is sampled from annual gridMET aggregates.",
        ha="center",
        va="bottom",
        fontsize=7.1,
        color=COLORS["axis"],
    )
    fig.subplots_adjust(left=0.02, right=0.985, top=0.925, bottom=0.055, wspace=0.08, hspace=0.14)
    out = FIG_DIR / "phase3_spatial_qc_maps.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def main():
    ensure_dirs()
    _, points, midpoint_df = segment_midpoints()
    print("[static] sampling DEM and LANDFIRE")
    static = build_static_covariates(points, midpoint_df)
    print("[weather] sampling gridMET annual aggregates")
    weather = build_weather_covariates(midpoint_df)
    model, summary = write_outputs(static, weather)
    fig = make_qc_figures(model)
    map_fig = make_spatial_qc_figure(model)
    print(json.dumps({k: v for k, v in summary.items() if k not in {"outputs"}}, indent=2))
    print(f"[figure] {fig}")
    print(f"[figure] {map_fig}")


if __name__ == "__main__":
    main()
