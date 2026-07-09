import json
import os
import sys
import xml.etree.ElementTree as ET
import warnings
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
warnings.filterwarnings("ignore", category=DeprecationWarning, message="Setting the shape on a NumPy array.*")

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import array_bounds
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window, from_bounds, intersection, transform as window_transform
from scipy import ndimage
from shapely.geometry import box

from utils_v2 import PROJECT, load_config, rel, require_audit_first, write_json, write_text


OUT_DIR = PROJECT / "data_intermediate/v2/support_aligned"
AUDIT_DIR = PROJECT / "outputs/v2/audit"
FIG_DIR = PROJECT / "outputs/v2/figures"
TABLE_DIR = PROJECT / "outputs/v2/tables"

LANDFIRE_BANDS = {
    "fbfm40": 1,
    "cc": 2,
    "ch": 3,
    "cbh": 4,
    "cbd": 5,
}


def ensure_dirs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def locate_landfire_tif(config):
    manifest = PROJECT / config["paths"]["landfire_manifest"]
    if manifest.exists():
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        tif = payload.get("tif")
        if tif and Path(tif).exists():
            return Path(tif)
    matches = sorted((PROJECT / config["paths"]["landfire_dir"]).glob("**/*.tif"))
    if not matches:
        raise FileNotFoundError("LANDFIRE tif not found")
    return matches[0]


def load_buffers(config):
    buffers = gpd.read_file(PROJECT / config["paths"]["segment_buffers_1km"])
    if buffers.crs is None:
        buffers = buffers.set_crs("EPSG:4326")
    return buffers[["segment_id", "geometry"]].copy()


def finite_values(arr, mask, nodata=None):
    vals = arr[mask]
    vals = vals.astype("float64", copy=False)
    vals = vals[np.isfinite(vals)]
    if nodata is not None:
        vals = vals[vals != nodata]
    return vals


def safe_stats(vals):
    if vals.size == 0:
        return {"mean": np.nan, "sd": np.nan, "p95": np.nan}
    return {
        "mean": float(np.nanmean(vals)),
        "sd": float(np.nanstd(vals)),
        "p95": float(np.nanpercentile(vals, 95)),
    }


def masked_values_from_dataset(src, geom, band):
    try:
        win = from_bounds(*geom.bounds, transform=src.transform).round_offsets().round_lengths()
        win = intersection(win, Window(0, 0, src.width, src.height))
    except Exception:
        return np.array([], dtype="float64")
    if win.width <= 0 or win.height <= 0:
        return np.array([], dtype="float64")
    arr = src.read(band, window=win, masked=False)
    w_transform = window_transform(win, src.transform)
    mask = geometry_mask([geom], out_shape=arr.shape, transform=w_transform, invert=True)
    return finite_values(arr, mask, src.nodata)


def masked_bands_from_dataset(src, geom, bands):
    try:
        win = from_bounds(*geom.bounds, transform=src.transform).round_offsets().round_lengths()
        win = intersection(win, Window(0, 0, src.width, src.height))
    except Exception:
        return {band: np.array([], dtype="float64") for band in bands}
    if win.width <= 0 or win.height <= 0:
        return {band: np.array([], dtype="float64") for band in bands}

    arr = src.read(bands, window=win, masked=False)
    w_transform = window_transform(win, src.transform)
    mask = geometry_mask([geom], out_shape=arr.shape[1:], transform=w_transform, invert=True)
    return {band: finite_values(arr[i], mask, src.nodata) for i, band in enumerate(bands)}


def masked_values_from_array(arr, transform, geom, nodata=np.nan):
    height, width = arr.shape
    try:
        win = from_bounds(*geom.bounds, transform=transform).round_offsets().round_lengths()
        win = intersection(win, Window(0, 0, width, height))
    except Exception:
        return np.array([], dtype="float64")
    if win.width <= 0 or win.height <= 0:
        return np.array([], dtype="float64")
    row0 = int(win.row_off)
    col0 = int(win.col_off)
    row1 = row0 + int(win.height)
    col1 = col0 + int(win.width)
    sub = arr[row0:row1, col0:col1]
    w_transform = window_transform(win, transform)
    mask = geometry_mask([geom], out_shape=sub.shape, transform=w_transform, invert=True)
    return finite_values(sub, mask, nodata)


def support_aligned_landfire(buffers, landfire_tif):
    with rasterio.open(landfire_tif) as src:
        b = buffers.to_crs(src.crs)
        rows = []
        for idx, row in b.iterrows():
            if idx and idx % 1000 == 0:
                print(f"[support] LANDFIRE buffers processed: {idx}/{len(b)}", flush=True)
            geom = row.geometry
            vals = masked_bands_from_dataset(
                src,
                geom,
                [
                    LANDFIRE_BANDS["cc"],
                    LANDFIRE_BANDS["ch"],
                    LANDFIRE_BANDS["cbh"],
                    LANDFIRE_BANDS["cbd"],
                ],
            )
            cc = vals[LANDFIRE_BANDS["cc"]]
            ch_raw = vals[LANDFIRE_BANDS["ch"]]
            cbh_raw = vals[LANDFIRE_BANDS["cbh"]]
            cbd_raw = vals[LANDFIRE_BANDS["cbd"]]

            ch = ch_raw / 10.0
            cbh = cbh_raw / 10.0
            cbd = cbd_raw / 100.0
            ch_positive = ch[ch > 0]
            cbh_positive = cbh[cbh > 0]
            valid_ch = ch[np.isfinite(ch)]

            rows.append(
                {
                    "segment_id": row.segment_id,
                    "cc_mean": float(np.nanmean(cc)) if cc.size else np.nan,
                    "cc_p90": float(np.nanpercentile(cc, 90)) if cc.size else np.nan,
                    "ch_positive_median": float(np.nanmedian(ch_positive)) if ch_positive.size else np.nan,
                    "ch_positive_fraction": float(ch_positive.size / valid_ch.size) if valid_ch.size else np.nan,
                    "cbh_positive_p10": float(np.nanpercentile(cbh_positive, 10)) if cbh_positive.size else np.nan,
                    "cbd_p90": float(np.nanpercentile(cbd, 90)) if cbd.size else np.nan,
                    "cbd_mean": float(np.nanmean(cbd)) if cbd.size else np.nan,
                    "landfire_valid_pixel_count": int(max(cc.size, ch.size, cbh.size, cbd.size)),
                }
            )
    return pd.DataFrame(rows)


def terrain_arrays_metric(dem_path, dst_crs="EPSG:3310", resolution=250.0):
    with rasterio.open(dem_path) as src:
        with WarpedVRT(
            src,
            crs=dst_crs,
            resolution=resolution,
            resampling=Resampling.bilinear,
            nodata=np.nan,
        ) as vrt:
            elev = vrt.read(1, masked=True).filled(np.nan).astype("float32")
            transform = vrt.transform
            xres = abs(transform.a)
            yres = abs(transform.e)
    gy, gx = np.gradient(elev.astype("float64"), yres, xres)
    slope = np.degrees(np.arctan(np.sqrt(gx * gx + gy * gy))).astype("float32")
    tri = ndimage.generic_filter(elev.astype("float64"), np.nanstd, size=3, mode="nearest").astype("float32")
    return elev, slope, tri, transform


def support_aligned_terrain(buffers, dem_path, project_crs):
    b = buffers.to_crs(project_crs)
    elev, slope, tri, transform = terrain_arrays_metric(dem_path, project_crs)
    rows = []
    for _, row in b.iterrows():
        geom = row.geometry
        elev_vals = masked_values_from_array(elev, transform, geom)
        slope_vals = masked_values_from_array(slope, transform, geom)
        tri_vals = masked_values_from_array(tri, transform, geom)
        elev_stats = safe_stats(elev_vals)
        slope_stats = safe_stats(slope_vals)
        tri_stats = safe_stats(tri_vals)
        rows.append(
            {
                "segment_id": row.segment_id,
                "elevation_mean_m": elev_stats["mean"],
                "elevation_sd_m": elev_stats["sd"],
                "elevation_p95_m": elev_stats["p95"],
                "slope_mean_deg": slope_stats["mean"],
                "slope_p95_deg": slope_stats["p95"],
                "terrain_ruggedness_mean": tri_stats["mean"],
                "dem_valid_pixel_count": int(elev_vals.size),
            }
        )
    return pd.DataFrame(rows)


def parse_fbfm_xml_codes(xml_path):
    if not xml_path.exists():
        return {}
    root = ET.parse(xml_path).getroot()
    labels = []
    for edomv in root.findall(".//edomv"):
        text = (edomv.text or "").strip()
        if text and text != "-9999" and text[:2] in {"NB", "GR", "GS", "SH", "TU", "TL", "SB"}:
            labels.append(text)
    return {"labels": sorted(set(labels))}


def write_fbfm_blocker(landfire_tif):
    xml_path = landfire_tif.parent / "LF2024_FBFM40_CONUS.xml"
    parsed = parse_fbfm_xml_codes(xml_path)
    text = "# FBFM40 Mapping Blocker\n\n"
    text += "The local LANDFIRE FBFM40 XML metadata lists FBFM40 class labels such as NB, GR, GS, SH, TU, TL, and SB. "
    text += "However, this audit pass did not find an explicit local table mapping the raster numeric band-1 values to those class labels. "
    text += "Per the V2 rules, the workflow does not infer or average FBFM40 numeric codes.\n\n"
    text += f"- LANDFIRE tif: `{rel(landfire_tif)}`\n"
    text += f"- XML labels detected: `{json.dumps(parsed.get('labels', []))}`\n\n"
    text += "The V2 model should use the configured fallback interaction with canopy positive fraction unless a verified mapping table is added.\n"
    write_text(AUDIT_DIR / "FBFM40_MAPPING_BLOCKER.md", text)


def grid_edges(vals):
    vals = np.asarray(vals, dtype="float64")
    edges = np.empty(vals.size + 1, dtype="float64")
    edges[1:-1] = (vals[:-1] + vals[1:]) / 2.0
    edges[0] = vals[0] - (edges[1] - vals[0])
    edges[-1] = vals[-1] + (vals[-1] - edges[-2])
    return edges


def gridmet_cell_polygons(gridmet_file, project_crs):
    ds = xr.open_dataset(str(gridmet_file.resolve()), engine="h5netcdf")
    lon = ds["lon"].values
    lat = ds["lat"].values
    ds.close()
    lon_edges = grid_edges(lon)
    lat_edges = grid_edges(lat)
    rows = []
    for iy, lat_c in enumerate(lat):
        y0, y1 = sorted([lat_edges[iy], lat_edges[iy + 1]])
        for ix, lon_c in enumerate(lon):
            x0, x1 = sorted([lon_edges[ix], lon_edges[ix + 1]])
            rows.append(
                {
                    "gridmet_cell_id": f"gm_{iy:03d}_{ix:03d}",
                    "gridmet_lat_index": iy,
                    "gridmet_lon_index": ix,
                    "gridmet_lat": float(lat_c),
                    "gridmet_lon": float(lon_c),
                    "geometry": box(x0, y0, x1, y1),
                }
            )
    cells = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326").to_crs(project_crs)
    return cells


def build_gridmet_weights(buffers, config):
    project_crs = config["spatial"]["project_crs"]
    sample = PROJECT / config["paths"]["interim_gridmet_dir"] / "fm100_2021_study_area.nc"
    cells = gridmet_cell_polygons(sample, project_crs)
    b = buffers.to_crs(project_crs).copy()
    b["buffer_area_m2"] = b.geometry.area
    candidate = gpd.sjoin(
        b[["segment_id", "buffer_area_m2", "geometry"]],
        cells[["gridmet_cell_id", "gridmet_lat_index", "gridmet_lon_index", "gridmet_lat", "gridmet_lon", "geometry"]],
        how="inner",
        predicate="intersects",
    )
    rows = []
    cells_by_id = cells.set_index("gridmet_cell_id")
    for _, row in candidate.iterrows():
        cell_geom = cells_by_id.loc[row.gridmet_cell_id].geometry
        area = row.geometry.intersection(cell_geom).area
        if area <= 0:
            continue
        rows.append(
            {
                "segment_id": row.segment_id,
                "gridmet_cell_id": row.gridmet_cell_id,
                "gridmet_lat_index": int(row.gridmet_lat_index),
                "gridmet_lon_index": int(row.gridmet_lon_index),
                "gridmet_lat": float(row.gridmet_lat),
                "gridmet_lon": float(row.gridmet_lon),
                "intersection_area_m2": float(area),
                "buffer_area_m2": float(row.buffer_area_m2),
                "weight": float(area / row.buffer_area_m2),
            }
        )
    weights = pd.DataFrame(rows)
    if not weights.empty:
        totals = weights.groupby("segment_id")["weight"].transform("sum")
        weights["normalized_weight"] = weights["weight"] / totals
    return weights


def compare_with_v1(static_v2, config):
    v1 = pd.read_parquet(PROJECT / config["paths"]["v1_static_covariates"])
    cols = [
        "segment_id",
        "dem_elevation_m",
        "landfire_canopy_cover_pct",
        "landfire_canopy_height_m",
        "landfire_canopy_bulk_density",
    ]
    cols = [c for c in cols if c in v1.columns]
    merged = static_v2.merge(v1[cols], on="segment_id", how="left")
    rows = []
    pairs = [
        ("elevation_mean_m", "dem_elevation_m"),
        ("cc_mean", "landfire_canopy_cover_pct"),
        ("ch_positive_median", "landfire_canopy_height_m"),
        ("cbd_mean", "landfire_canopy_bulk_density"),
    ]
    for v2_col, v1_col in pairs:
        if v2_col not in merged or v1_col not in merged:
            continue
        a = merged[v2_col]
        b = merged[v1_col]
        diff = a - b
        rows.append(
            {
                "v2_buffer_column": v2_col,
                "v1_midpoint_column": v1_col,
                "paired_nonmissing": int((a.notna() & b.notna()).sum()),
                "mean_difference": float(diff.mean(skipna=True)),
                "median_abs_difference": float(diff.abs().median(skipna=True)),
                "correlation": float(a.corr(b)),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(TABLE_DIR / "support_alignment_v1_midpoint_comparison.csv", index=False)
    return out


def write_support_qa(static_v2, weights, compare, config, landfire_tif):
    weight_counts = weights.groupby("segment_id").size() if not weights.empty else pd.Series(dtype="int64")
    weight_sums = weights.groupby("segment_id")["weight"].sum() if not weights.empty else pd.Series(dtype="float64")
    summary = {
        "segments": int(static_v2["segment_id"].nunique()),
        "static_rows": int(len(static_v2)),
        "landfire_tif": rel(landfire_tif),
        "dem": config["paths"]["dem"],
        "gridmet_weight_rows": int(len(weights)),
        "gridmet_segments_with_weights": int(weights["segment_id"].nunique()) if not weights.empty else 0,
        "gridmet_cells_per_buffer_quantiles": weight_counts.quantile([0, 0.5, 0.9, 1.0]).to_dict() if not weights.empty else {},
        "gridmet_weight_sum_quantiles": weight_sums.quantile([0, 0.5, 0.9, 1.0]).to_dict() if not weights.empty else {},
        "missing_fraction_by_column": static_v2.drop(columns=["segment_id"]).isna().mean().to_dict(),
        "fbfm40_mapping_status": "blocked_no_explicit_numeric_code_mapping",
    }
    write_json(AUDIT_DIR / "SUPPORT_ALIGNMENT_QA.json", summary)
    md = "# Support Alignment QA\n\n"
    md += f"- Segment buffers processed: {summary['segments']}\n"
    md += f"- Static covariate rows: {summary['static_rows']}\n"
    md += f"- LANDFIRE raster: `{summary['landfire_tif']}`\n"
    md += f"- DEM raster: `{summary['dem']}`\n"
    md += f"- gridMET weight rows: {summary['gridmet_weight_rows']}\n"
    md += f"- Segments with gridMET weights: {summary['gridmet_segments_with_weights']}\n"
    md += f"- gridMET cells per buffer quantiles: `{summary['gridmet_cells_per_buffer_quantiles']}`\n"
    md += f"- gridMET raw weight-sum quantiles: `{summary['gridmet_weight_sum_quantiles']}`\n"
    md += "\n## FBFM40\n\n"
    md += "FBFM40 family fractions were not computed because no explicit local numeric-code-to-label table was found. See `FBFM40_MAPPING_BLOCKER.md`.\n"
    md += "\n## V1 Midpoint vs V2 Buffer-Aligned Comparison\n\n"
    md += compare.to_markdown(index=False) if not compare.empty else "No comparison rows generated."
    md += "\n"
    write_text(AUDIT_DIR / "SUPPORT_ALIGNMENT_QA.md", md)


def main():
    require_audit_first()
    ensure_dirs()
    config = load_config()
    project_crs = config["spatial"]["project_crs"]
    buffers = load_buffers(config)
    landfire_tif = locate_landfire_tif(config)

    print("[support] LANDFIRE buffer zonal stats")
    landfire = support_aligned_landfire(buffers, landfire_tif)
    write_fbfm_blocker(landfire_tif)

    print("[support] DEM terrain buffer zonal stats")
    terrain = support_aligned_terrain(buffers, PROJECT / config["paths"]["dem"], project_crs)
    static = terrain.merge(landfire, on="segment_id", how="outer")
    static.to_parquet(OUT_DIR / "static_buffer_covariates.parquet", index=False)
    static.to_csv(OUT_DIR / "static_buffer_covariates.csv", index=False)

    print("[support] gridMET cell-buffer area weights")
    weights = build_gridmet_weights(buffers, config)
    weights.to_parquet(OUT_DIR / "segment_gridmet_weights.parquet", index=False)
    weights.to_csv(OUT_DIR / "segment_gridmet_weights.csv", index=False)

    compare = compare_with_v1(static, config)
    write_support_qa(static, weights, compare, config, landfire_tif)
    print(f"[done] {OUT_DIR / 'static_buffer_covariates.parquet'}")
    print(f"[done] {OUT_DIR / 'segment_gridmet_weights.parquet'}")


if __name__ == "__main__":
    main()
