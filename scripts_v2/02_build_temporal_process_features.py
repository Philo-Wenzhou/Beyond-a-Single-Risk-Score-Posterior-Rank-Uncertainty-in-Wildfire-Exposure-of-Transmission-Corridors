import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import numpy as np
import pandas as pd
import xarray as xr

from utils_v2 import PROJECT, load_config, require_audit_first, write_json, write_text


OUT_DIR = PROJECT / "data_intermediate/v2/temporal_process"
AUDIT_DIR = PROJECT / "outputs/v2/audit"
TABLE_DIR = PROJECT / "outputs/v2/tables"

VAR_NAME = {
    "vpd": "mean_vapor_pressure_deficit",
    "erc": "energy_release_component-g",
    "bi": "burning_index_g",
    "vs": "wind_speed",
    "fm100": "dead_fuel_moisture_100hr",
    "fm1000": "dead_fuel_moisture_1000hr",
    "rmin": "relative_humidity",
    "pr": "precipitation_amount",
}

HIGH_VARS = ["vpd", "erc", "bi", "vs"]
LOW_VARS = ["fm100", "fm1000", "rmin"]


def ensure_dirs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def season_slice(ds, year, start_mm_dd, end_mm_dd):
    start = np.datetime64(f"{year}-{start_mm_dd}")
    end = np.datetime64(f"{year}-{end_mm_dd}")
    return ds.sel(day=slice(start, end))


def read_season_array(gridmet_dir, var, year, config):
    path = gridmet_dir / f"{var}_{year}_study_area.nc"
    if not path.exists():
        raise FileNotFoundError(path)
    ds = xr.open_dataset(str(path.resolve()), engine="h5netcdf")
    try:
        sub = season_slice(
            ds,
            year,
            config["season"]["primary"]["start_mm_dd"],
            config["season"]["primary"]["end_mm_dd"],
        )
        arr = sub[VAR_NAME[var]].values.astype("float32")
    finally:
        ds.close()
    return arr


def load_grid_shape(gridmet_dir):
    sample = gridmet_dir / "fm100_2021_study_area.nc"
    ds = xr.open_dataset(str(sample.resolve()), engine="h5netcdf")
    try:
        lat = ds["lat"].values
        lon = ds["lon"].values
    finally:
        ds.close()
    return len(lat), len(lon)


def make_cell_ids(nlat, nlon):
    return np.array([f"gm_{iy:03d}_{ix:03d}" for iy in range(nlat) for ix in range(nlon)])


def train_thresholds(config):
    gridmet_dir = PROJECT / config["paths"]["interim_gridmet_dir"]
    train_years = config["years"]["train"]
    nlat, nlon = load_grid_shape(gridmet_dir)
    thresholds = {}
    records = {"gridmet_cell_id": make_cell_ids(nlat, nlon)}
    for var in config["gridmet"]["variables"]:
        chunks = [read_season_array(gridmet_dir, var, year, config) for year in train_years]
        stack = np.concatenate(chunks, axis=0)
        flat = stack.reshape(stack.shape[0], -1)
        if var in HIGH_VARS:
            q90 = np.nanpercentile(flat, 90, axis=0).astype("float32")
            q95 = np.nanpercentile(flat, 95, axis=0).astype("float32")
            thresholds[(var, "q90")] = q90
            thresholds[(var, "q95")] = q95
            records[f"{var}_train_q90"] = q90
            records[f"{var}_train_q95"] = q95
        elif var in LOW_VARS:
            q10 = np.nanpercentile(flat, 10, axis=0).astype("float32")
            q05 = np.nanpercentile(flat, 5, axis=0).astype("float32")
            thresholds[(var, "q10")] = q10
            thresholds[(var, "q05")] = q05
            records[f"{var}_train_q10"] = q10
            records[f"{var}_train_q05"] = q05
        elif var == "pr":
            dry = np.nanpercentile(flat, 20, axis=0).astype("float32")
            thresholds[(var, "q20")] = dry
            records[f"{var}_train_q20"] = dry
    out = pd.DataFrame(records)
    out.to_parquet(OUT_DIR / "gridmet_cell_train_thresholds.parquet", index=False)
    out.to_csv(OUT_DIR / "gridmet_cell_train_thresholds.csv", index=False)
    return thresholds, nlat, nlon


def longest_true_run(mask):
    if mask.size == 0:
        return 0
    padded = np.concatenate([[False], mask.astype(bool), [False]])
    diff = np.diff(padded.astype(np.int8))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    return int((ends - starts).max()) if starts.size else 0


def cell_year_features(config, thresholds, nlat, nlon):
    gridmet_dir = PROJECT / config["paths"]["interim_gridmet_dir"]
    cell_ids = make_cell_ids(nlat, nlon)
    rows = []
    for year in config["years"]["all"]:
        print(f"[temporal] cell-year summaries {year}", flush=True)
        arrays = {var: read_season_array(gridmet_dir, var, year, config).reshape(-1, nlat * nlon) for var in config["gridmet"]["variables"]}
        record = {"year": np.repeat(year, nlat * nlon), "gridmet_cell_id": cell_ids}

        for var in HIGH_VARS:
            arr = arrays[var]
            record[f"{var}_season_p95"] = np.nanpercentile(arr, 95, axis=0)
            record[f"{var}_above_train_q90_frac"] = np.nanmean(arr > thresholds[(var, "q90")][None, :], axis=0)
            record[f"{var}_above_train_q95_frac"] = np.nanmean(arr > thresholds[(var, "q95")][None, :], axis=0)

        for var in LOW_VARS:
            arr = arrays[var]
            record[f"{var}_season_p05"] = np.nanpercentile(arr, 5, axis=0)
            record[f"{var}_below_train_q10_frac"] = np.nanmean(arr < thresholds[(var, "q10")][None, :], axis=0)
            record[f"{var}_below_train_q05_frac"] = np.nanmean(arr < thresholds[(var, "q05")][None, :], axis=0)

        pr = arrays["pr"]
        record["pr_season_sum"] = np.nansum(pr, axis=0)
        record["pr_below_train_q20_frac"] = np.nanmean(pr < thresholds[("pr", "q20")][None, :], axis=0)

        hwd = (
            (arrays["vpd"] > thresholds[("vpd", "q90")][None, :])
            & (arrays["vs"] > thresholds[("vs", "q90")][None, :])
            & (arrays["fm100"] < thresholds[("fm100", "q10")][None, :])
        )
        record["hot_dry_windy_train_threshold_frac"] = np.nanmean(hwd, axis=0)

        dry = pr < thresholds[("pr", "q20")][None, :]
        record["dry_spell_max_days"] = np.array([longest_true_run(dry[:, i]) for i in range(dry.shape[1])], dtype="int16")
        rows.append(pd.DataFrame(record))
    out = pd.concat(rows, ignore_index=True)
    out.to_parquet(OUT_DIR / "gridmet_cell_year_process_features.parquet", index=False)
    return out


def aggregate_to_segments(cell_year, config):
    filled_weights = PROJECT / "data_intermediate/v2/support_aligned/segment_gridmet_weights_filled.parquet"
    original_weights = PROJECT / "data_intermediate/v2/support_aligned/segment_gridmet_weights.parquet"
    weights_path = filled_weights if filled_weights.exists() else original_weights
    weights = pd.read_parquet(weights_path)
    skeleton = pd.read_csv(PROJECT / config["paths"]["segment_year_labels"], usecols=["segment_id", "year"])
    feature_cols = [c for c in cell_year.columns if c not in {"gridmet_cell_id", "year"}]
    merged = weights[["segment_id", "gridmet_cell_id", "normalized_weight"]].merge(
        cell_year, on="gridmet_cell_id", how="left"
    )
    for col in feature_cols:
        merged[col] = merged[col] * merged["normalized_weight"]
    grouped = merged.groupby(["segment_id", "year"], as_index=False)[feature_cols].sum(min_count=1)
    out = skeleton.merge(grouped, on=["segment_id", "year"], how="left")
    out.to_parquet(OUT_DIR / "segment_year_temporal_process_features.parquet", index=False)
    out.to_csv(OUT_DIR / "segment_year_temporal_process_features.csv", index=False)
    return out, weights


def write_qa(segment_year, weights, config):
    labels = pd.read_csv(PROJECT / config["paths"]["segment_year_labels"], usecols=["segment_id", "year"])
    missing_segments = sorted(set(labels["segment_id"]) - set(weights["segment_id"]))
    feature_cols = [c for c in segment_year.columns if c not in {"segment_id", "year"}]
    missing_by_col = segment_year[feature_cols].isna().mean().sort_values(ascending=False)
    summary = {
        "segment_year_rows": int(len(segment_year)),
        "unique_segments": int(segment_year["segment_id"].nunique()),
        "years": sorted(int(x) for x in segment_year["year"].unique()),
        "segments_without_gridmet_weights": len(missing_segments),
        "example_segments_without_gridmet_weights": missing_segments[:20],
        "max_missing_fraction": float(missing_by_col.max()),
        "features": feature_cols,
        "threshold_freeze_rule": "gridMET cell thresholds estimated only from 2017-2021 primary season before deriving 2022-2023 features",
    }
    write_json(AUDIT_DIR / "TEMPORAL_PROCESS_QA.json", summary)
    rows = [
        "# Temporal Process QA",
        "",
        f"- Segment-year rows: {summary['segment_year_rows']}",
        f"- Unique segments: {summary['unique_segments']}",
        f"- Years: `{summary['years']}`",
        f"- Segments without gridMET weights: {summary['segments_without_gridmet_weights']}",
        f"- Max feature missing fraction: {summary['max_missing_fraction']:.6f}",
        "- Threshold freeze rule: 2017-2021 primary season only.",
        "",
        "## Missingness",
        "",
        missing_by_col.head(20).to_frame("missing_fraction").to_markdown(),
    ]
    write_text(AUDIT_DIR / "TEMPORAL_PROCESS_QA.md", "\n".join(rows) + "\n")
    pd.DataFrame({"segment_id": missing_segments}).to_csv(TABLE_DIR / "segments_without_gridmet_weights.csv", index=False)


def main():
    require_audit_first()
    ensure_dirs()
    config = load_config()
    if not (PROJECT / "data_intermediate/v2/support_aligned/segment_gridmet_weights.parquet").exists():
        raise SystemExit("Run scripts_v2/01_build_support_aligned_covariates.py first.")
    print("[temporal] freeze train thresholds from 2017-2021", flush=True)
    thresholds, nlat, nlon = train_thresholds(config)
    cell_year = cell_year_features(config, thresholds, nlat, nlon)
    print("[temporal] aggregate to segment-year with area weights", flush=True)
    segment_year, weights = aggregate_to_segments(cell_year, config)
    write_qa(segment_year, weights, config)
    print(f"[done] {OUT_DIR / 'segment_year_temporal_process_features.parquet'}")


if __name__ == "__main__":
    main()
