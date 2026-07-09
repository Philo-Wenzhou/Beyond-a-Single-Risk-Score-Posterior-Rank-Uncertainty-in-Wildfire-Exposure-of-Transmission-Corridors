import ast
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from utils_v2 import load_config, rel, write_json, write_text

try:
    import xarray as xr
except Exception:
    xr = None


OUT = PROJECT / "outputs/v2/audit"
OUT.mkdir(parents=True, exist_ok=True)


def load_table(path):
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    return None


def table_schema(path):
    try:
        df = load_table(path)
    except Exception as exc:
        return [
            {
                "file": rel(path),
                "kind": path.suffix.lower().lstrip("."),
                "column": "__read_error__",
                "dtype": str(exc),
            }
        ]
    rows = []
    if df is None:
        return rows
    dup_segment_year = ""
    if {"segment_id", "year"}.issubset(df.columns):
        dup_segment_year = int(df.duplicated(["segment_id", "year"]).sum())
    years = ""
    if "year" in df.columns:
        numeric_years = pd.to_numeric(df["year"], errors="coerce").dropna()
        years = ",".join(map(str, sorted(numeric_years.astype(int).unique())))
    unique_segments = int(df["segment_id"].nunique()) if "segment_id" in df.columns else ""
    for col in df.columns:
        s = df[col]
        rows.append(
            {
                "file": rel(path),
                "kind": path.suffix.lower().lstrip("."),
                "column": col,
                "dtype": str(s.dtype),
                "rows": len(df),
                "non_null": int(s.notna().sum()),
                "missing": int(s.isna().sum()),
                "missing_fraction": float(s.isna().mean()),
                "unique_values": int(s.nunique(dropna=True)),
                "years": years,
                "unique_segments": unique_segments,
                "duplicate_segment_year_keys": dup_segment_year,
            }
        )
    return rows


def gpkg_schema(path):
    rows = []
    try:
        layers = gpd.io.file.fiona.listlayers(path)
    except Exception:
        layers = [None]
    for layer in layers:
        try:
            gdf = gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
        except Exception as exc:
            rows.append({"file": rel(path), "kind": "gpkg", "column": "__read_error__", "dtype": str(exc)})
            continue
        dup_segment_year = ""
        if {"segment_id", "year"}.issubset(gdf.columns):
            dup_segment_year = int(gdf.duplicated(["segment_id", "year"]).sum())
        for col in gdf.columns:
            rows.append(
                {
                    "file": rel(path),
                    "kind": "gpkg",
                    "layer": layer or "",
                    "column": col,
                    "dtype": str(gdf[col].dtype),
                    "rows": len(gdf),
                    "crs": str(gdf.crs),
                    "bounds": json.dumps(list(map(float, gdf.total_bounds))) if len(gdf) else "",
                    "non_null": int(gdf[col].notna().sum()),
                    "missing": int(gdf[col].isna().sum()),
                    "missing_fraction": float(gdf[col].isna().mean()) if len(gdf) else 0.0,
                    "unique_segments": int(gdf["segment_id"].nunique()) if "segment_id" in gdf.columns else "",
                    "duplicate_segment_year_keys": dup_segment_year,
                }
            )
    return rows


def raster_schema(path):
    rows = []
    try:
        with rasterio.open(path) as src:
            for idx in range(1, src.count + 1):
                rows.append(
                    {
                        "file": rel(path),
                        "kind": "raster",
                        "column": f"band_{idx}",
                        "dtype": src.dtypes[idx - 1],
                        "rows": src.height * src.width,
                        "crs": str(src.crs),
                        "bounds": json.dumps(list(map(float, src.bounds))),
                        "width": src.width,
                        "height": src.height,
                        "band_count": src.count,
                        "nodata": src.nodata,
                        "band_description": src.descriptions[idx - 1] or "",
                    }
                )
    except Exception as exc:
        rows.append({"file": rel(path), "kind": "raster", "column": "__read_error__", "dtype": str(exc)})
    return rows


def netcdf_schema(path):
    rows = []
    if xr is None:
        return [{"file": rel(path), "kind": "netcdf", "column": "__xarray_unavailable__", "dtype": ""}]
    try:
        with xr.open_dataset(path) as ds:
            time_info = ""
            if "day" in ds.coords:
                vals = pd.to_datetime(ds["day"].values)
                if len(vals):
                    time_info = f"{vals.min().date()} to {vals.max().date()}"
            elif "time" in ds.coords:
                vals = pd.to_datetime(ds["time"].values)
                if len(vals):
                    time_info = f"{vals.min().date()} to {vals.max().date()}"
            for name, da in ds.data_vars.items():
                rows.append(
                    {
                        "file": rel(path),
                        "kind": "netcdf",
                        "column": name,
                        "dtype": str(da.dtype),
                        "rows": int(np.prod(list(da.sizes.values()))) if da.sizes else "",
                        "dims": json.dumps(dict(da.sizes)),
                        "coords": ",".join(ds.coords),
                        "time_range": time_info,
                        "attrs": json.dumps({k: str(v) for k, v in da.attrs.items()})[:1200],
                    }
                )
    except Exception as exc:
        rows.append({"file": rel(path), "kind": "netcdf", "column": "__read_error__", "dtype": str(exc)})
    return rows


def file_manifest():
    skip_parts = {".python_deps", "tmp", "__pycache__"}
    keep_suffix = {
        ".py",
        ".ps1",
        ".bat",
        ".cmd",
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".tex",
        ".bib",
        ".csv",
        ".parquet",
        ".gpkg",
        ".tif",
        ".tiff",
        ".nc",
        ".stan",
    }
    rows = []
    for path in PROJECT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_parts for part in path.parts):
            continue
        if path.suffix.lower() not in keep_suffix:
            continue
        st = path.stat()
        rows.append(
            {
                "file": rel(path),
                "suffix": path.suffix.lower(),
                "bytes": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows).sort_values("file")


def extract_feature_lists():
    target = PROJECT / "scripts/phase4_bayesian_ranking.py"
    source = target.read_text(encoding="utf-8")
    tree = ast.parse(source)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target_node in node.targets:
                if isinstance(target_node, ast.Name) and target_node.id in {"RAW_FEATURES", "MODEL_FEATURES"}:
                    try:
                        out[target_node.id] = ast.literal_eval(node.value)
                    except Exception:
                        if isinstance(node.value, ast.BinOp):
                            out[target_node.id] = "defined by expression in script"
    if out.get("MODEL_FEATURES") == "defined by expression in script" and isinstance(out.get("RAW_FEATURES"), list):
        match = re.search(r"MODEL_FEATURES\s*=\s*RAW_FEATURES\s*\+\s*(\[[^\]]+\])", source, re.S)
        if match:
            out["MODEL_FEATURES"] = out["RAW_FEATURES"] + ast.literal_eval(match.group(1))
    return out


def locate_landfire_tif(config):
    manifest = PROJECT / config["paths"]["landfire_manifest"]
    if manifest.exists():
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        tif = payload.get("tif")
        if tif and Path(tif).exists():
            return Path(tif)
    matches = sorted((PROJECT / config["paths"]["landfire_dir"]).glob("**/*.tif"))
    return matches[0] if matches else None


def make_schema(config):
    paths = []
    for key, value in config["paths"].items():
        if key.endswith("_dir") or key in {"landfire_manifest"}:
            continue
        p = PROJECT / value
        if p.exists() and p.is_file():
            paths.append(p)
    paths.extend(sorted((PROJECT / "data/processed").rglob("*.parquet")))
    processed_csv = [
        p
        for p in sorted((PROJECT / "data/processed").rglob("*.csv"))
        if "stan_mcmc" not in p.as_posix().lower() and p.stat().st_size < 50_000_000
    ]
    paths.extend(processed_csv)
    paths.extend(sorted((PROJECT / "data/processed").rglob("*.gpkg")))
    paths.extend(sorted((PROJECT / "data/interim/gridmet_study_area").glob("*.nc"))[:8])
    paths.append(PROJECT / config["paths"]["dem"])
    landfire = locate_landfire_tif(config)
    if landfire:
        paths.append(landfire)

    seen = set()
    rows = []
    for path in paths:
        if not path.exists() or path in seen:
            continue
        seen.add(path)
        suffix = path.suffix.lower()
        if suffix in {".parquet", ".csv"}:
            rows.extend(table_schema(path))
        elif suffix == ".gpkg":
            rows.extend(gpkg_schema(path))
        elif suffix in {".tif", ".tiff"}:
            rows.extend(raster_schema(path))
        elif suffix == ".nc":
            rows.extend(netcdf_schema(path))
    return pd.DataFrame(rows)


def summarize_key_inputs(config, schema, manifest, features):
    def exists(path):
        return (PROJECT / path).exists()

    model_table = PROJECT / config["paths"]["v1_model_table"]
    duplicate_keys = None
    rows = segments = years = None
    if model_table.exists():
        df = pd.read_parquet(model_table)
        rows = len(df)
        segments = int(df["segment_id"].nunique()) if "segment_id" in df else None
        years = sorted(df["year"].dropna().astype(int).unique().tolist()) if "year" in df else None
        duplicate_keys = int(df.duplicated(["segment_id", "year"]).sum()) if {"segment_id", "year"}.issubset(df.columns) else None

    landfire = locate_landfire_tif(config)
    gridmet_files = sorted((PROJECT / "data/interim/gridmet_study_area").glob("*.nc"))
    manuscript_revised = PROJECT / "manuscript/main_submission_revised.tex"
    manuscript_clean = PROJECT / "manuscript/main_submission_clean.tex"
    blockers = []
    if duplicate_keys:
        blockers.append(f"Duplicate (segment_id, year) keys in V1 model table: {duplicate_keys}")
    if not manuscript_revised.exists():
        blockers.append("Prompt names manuscript/main_submission_revised.tex, but this file is absent; V1 candidate is main_submission_clean.tex.")
    if not landfire:
        blockers.append("LANDFIRE multi-band GeoTIFF not found.")

    return {
        "created": datetime.now().isoformat(timespec="seconds"),
        "paths_exist": {key: exists(value) for key, value in config["paths"].items() if not key.endswith("_dir")},
        "v1_model_table_rows": rows,
        "v1_unique_segments": segments,
        "v1_years": years,
        "v1_duplicate_segment_year_keys": duplicate_keys,
        "interim_gridmet_file_count": len(gridmet_files),
        "gridmet_file_examples": [rel(p) for p in gridmet_files[:8]],
        "landfire_tif": rel(landfire) if landfire else None,
        "feature_lists": features,
        "schema_rows": int(len(schema)),
        "manifest_rows": int(len(manifest)),
        "blockers": blockers,
    }


def write_audit_md(summary, schema):
    feature_lists = summary["feature_lists"]
    raw = feature_lists.get("RAW_FEATURES", [])
    model = feature_lists.get("MODEL_FEATURES", [])
    blockers = summary["blockers"]
    blocker_text = "\n".join(f"- {b}" for b in blockers) if blockers else "- None at audit stage."
    md = f"""# V2 Input Audit

Generated: {summary["created"]}

## Scope

This audit initializes the V2 spatiotemporal/hierarchical workflow without
modifying the V1 manuscript or V1 outputs. V2 remains a retrospective annual
external exposure-ranking workflow for transmission-line receptor assets.

## Key Input Status

- V1 model table rows: {summary["v1_model_table_rows"]}
- Unique segments: {summary["v1_unique_segments"]}
- Years: {summary["v1_years"]}
- Duplicate `(segment_id, year)` keys: {summary["v1_duplicate_segment_year_keys"]}
- Interim daily gridMET NetCDF files: {summary["interim_gridmet_file_count"]}
- LANDFIRE multi-band GeoTIFF: `{summary["landfire_tif"]}`

## Prompt/File-Name Note

The V2 prompt refers to `manuscript/main_submission_revised.tex`. That file is
not present in the current repository. The detected V1 submission candidate is
`manuscript/main_submission_clean.tex`. V2 will not overwrite either file.

## Current Spatial Extraction and Temporal Aggregation

The V1 processing scripts indicate that static DEM/LANDFIRE covariates were
sampled at segment midpoints, and annual gridMET covariates were sampled from
the nearest gridMET cell to the segment midpoint. Annual gridMET summaries use
p05/mean for FM100 and FM1000, p95/mean for VPD, ERC, BI, wind speed, and RMIN,
and sum/p95 for precipitation.

## Current Bayesian Fixed-Effect Feature List

RAW_FEATURES:

{json.dumps(raw, indent=2)}

MODEL_FEATURES:

{json.dumps(model, indent=2)}

## LANDFIRE Band Order and Units

The V1 scripts expect the LFPS multi-band GeoTIFF order:

1. LF2024_FBFM40
2. LF2024_CC
3. LF2024_CH
4. LF2024_CBH
5. LF2024_CBD

Decoded units required for V2:

- CH = raw / 10 m
- CBH = raw / 10 m
- CBD = raw / 100 kg m-3
- FBFM40 is categorical and must not be averaged or z-standardized as a continuous physical variable.

## Blockers / Warnings

{blocker_text}

## Output Files

- `outputs/v2/audit/V2_INPUT_SCHEMA.csv`
- `outputs/v2/audit/V2_FILE_MANIFEST.csv`
- `outputs/v2/audit/V2_INPUT_SUMMARY.json`
"""
    write_text(OUT / "V2_INPUT_AUDIT.md", md)


def main():
    config = load_config()
    manifest = file_manifest()
    schema = make_schema(config)
    features = extract_feature_lists()
    summary = summarize_key_inputs(config, schema, manifest, features)

    manifest.to_csv(OUT / "V2_FILE_MANIFEST.csv", index=False)
    schema.to_csv(OUT / "V2_INPUT_SCHEMA.csv", index=False)
    write_json(OUT / "V2_INPUT_SUMMARY.json", summary)
    write_audit_md(summary, schema)

    if summary["v1_duplicate_segment_year_keys"]:
        raise SystemExit("BLOCKER: duplicate (segment_id, year) keys detected. See V2_INPUT_AUDIT.md.")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
