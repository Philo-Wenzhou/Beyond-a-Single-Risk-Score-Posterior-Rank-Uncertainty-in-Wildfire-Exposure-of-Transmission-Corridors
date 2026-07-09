import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import pandas as pd
import xarray as xr
from shapely.geometry import Point

from utils_v2 import PROJECT, load_config, require_audit_first, write_json, write_text
from importlib.machinery import SourceFileLoader


SUPPORT_DIR = PROJECT / "data_intermediate/v2/support_aligned"
AUDIT_DIR = PROJECT / "outputs/v2/audit"
TABLE_DIR = PROJECT / "outputs/v2/tables"


def load_grid_cells(config):
    mod = SourceFileLoader(
        "support01",
        str(PROJECT / "scripts_v2/01_build_support_aligned_covariates.py"),
    ).load_module()
    sample = PROJECT / config["paths"]["interim_gridmet_dir"] / "fm100_2021_study_area.nc"
    return mod.gridmet_cell_polygons(sample, config["spatial"]["project_crs"])


def supplement_gridmet_weights(config):
    original = pd.read_parquet(SUPPORT_DIR / "segment_gridmet_weights.parquet")
    segments = gpd.read_file(PROJECT / config["paths"]["segment_buffers_1km"])
    if segments.crs is None:
        segments = segments.set_crs("EPSG:4326")
    buffers = segments[["segment_id", "geometry"]].to_crs(config["spatial"]["project_crs"])
    missing = sorted(set(buffers["segment_id"]) - set(original["segment_id"]))
    if not missing:
        filled = original.copy()
        filled["weight_source"] = "area_intersection"
        return filled, []

    cells = load_grid_cells(config)
    cells_cent = cells.copy()
    cells_cent["geometry"] = cells_cent.geometry.centroid
    miss = buffers[buffers["segment_id"].isin(missing)].copy()
    miss["geometry"] = miss.geometry.centroid
    nearest = gpd.sjoin_nearest(
        miss[["segment_id", "geometry"]],
        cells_cent[["gridmet_cell_id", "gridmet_lat_index", "gridmet_lon_index", "gridmet_lat", "gridmet_lon", "geometry"]],
        how="left",
        distance_col="nearest_distance_m",
    )
    add = pd.DataFrame(
        {
            "segment_id": nearest["segment_id"].values,
            "gridmet_cell_id": nearest["gridmet_cell_id"].values,
            "gridmet_lat_index": nearest["gridmet_lat_index"].astype(int).values,
            "gridmet_lon_index": nearest["gridmet_lon_index"].astype(int).values,
            "gridmet_lat": nearest["gridmet_lat"].astype(float).values,
            "gridmet_lon": nearest["gridmet_lon"].astype(float).values,
            "intersection_area_m2": 0.0,
            "buffer_area_m2": pd.NA,
            "weight": 1.0,
            "normalized_weight": 1.0,
            "nearest_distance_m": nearest["nearest_distance_m"].astype(float).values,
            "weight_source": "nearest_gridmet_cell_for_boundary_gap",
        }
    )
    base = original.copy()
    base["nearest_distance_m"] = 0.0
    base["weight_source"] = "area_intersection"
    filled = pd.concat([base, add], ignore_index=True, sort=False)
    return filled, add.to_dict(orient="records")


def parse_fbfm_labels(config):
    landfire_dir = PROJECT / config["paths"]["landfire_dir"]
    xmls = list(landfire_dir.glob("**/LF2024_FBFM40_CONUS.xml"))
    if not xmls:
        return pd.DataFrame()
    import xml.etree.ElementTree as ET

    root = ET.parse(xmls[0]).getroot()
    rows = []
    for edom in root.findall(".//edom"):
        code = (edom.findtext("edomv") or "").strip()
        desc = (edom.findtext("edomvd") or "").strip()
        if code and code != "-9999" and len(code) >= 2:
            family = code[:2]
            if family in {"NB", "GR", "GS", "SH", "TU", "TL", "SB"}:
                rows.append({"fbfm40_label": code, "fuel_family": family, "description": desc})
    out = pd.DataFrame(rows).drop_duplicates()
    out.to_csv(TABLE_DIR / "lf2024_fbfm40_labels_from_xml.csv", index=False)
    return out


def main():
    require_audit_first()
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()

    filled, nearest_records = supplement_gridmet_weights(config)
    filled.to_parquet(SUPPORT_DIR / "segment_gridmet_weights_filled.parquet", index=False)
    filled.to_csv(SUPPORT_DIR / "segment_gridmet_weights_filled.csv", index=False)
    labels = parse_fbfm_labels(config)

    summary = {
        "gridmet_weight_rows_filled": int(len(filled)),
        "segments_with_weights_filled": int(filled["segment_id"].nunique()),
        "nearest_filled_segments": len(nearest_records),
        "nearest_fill_records": nearest_records,
        "fbfm40_xml_labels": int(len(labels)),
        "fbfm40_mapping_status": "labels_extracted_from_xml_numeric_value_to_label_table_still_not_explicit",
    }
    write_json(AUDIT_DIR / "PUBLIC_GAP_SUPPLEMENTS_QA.json", summary)
    md = "# Public Gap Supplements QA\n\n"
    md += f"- Filled gridMET weight rows: {summary['gridmet_weight_rows_filled']}\n"
    md += f"- Segments with filled gridMET weights: {summary['segments_with_weights_filled']}\n"
    md += f"- Boundary segments supplemented by nearest gridMET cell: {summary['nearest_filled_segments']}\n"
    md += f"- FBFM40 labels extracted from local LF2024 XML: {summary['fbfm40_xml_labels']}\n"
    md += "- FBFM40 numeric raster-value to label mapping remains unverified locally; no FBFM family fractions are added to the primary model table yet.\n"
    write_text(AUDIT_DIR / "PUBLIC_GAP_SUPPLEMENTS_QA.md", md)
    print(f"[done] {SUPPORT_DIR / 'segment_gridmet_weights_filled.parquet'}")


if __name__ == "__main__":
    main()
