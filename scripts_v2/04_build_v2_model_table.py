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

from utils_v2 import PROJECT, load_config, require_audit_first, write_json, write_text


OUT_DIR = PROJECT / "data_intermediate/v2/model_table"
AUDIT_DIR = PROJECT / "outputs/v2/audit"
TABLE_DIR = PROJECT / "outputs/v2/tables"

DYNAMIC_FEATURES = [
    "vpd_season_p95",
    "erc_season_p95",
    "bi_season_p95",
    "vs_season_p95",
    "fm100_season_p05",
    "fm1000_season_p05",
    "rmin_season_p05",
    "pr_season_sum",
    "vpd_above_train_q90_frac",
    "erc_above_train_q90_frac",
    "bi_above_train_q90_frac",
    "vs_above_train_q90_frac",
    "fm100_below_train_q10_frac",
    "fm1000_below_train_q10_frac",
    "rmin_below_train_q10_frac",
    "pr_below_train_q20_frac",
    "hot_dry_windy_train_threshold_frac",
    "dry_spell_max_days",
]

STATIC_FEATURES = [
    "elevation_mean_m",
    "elevation_sd_m",
    "elevation_p95_m",
    "slope_mean_deg",
    "slope_p95_deg",
    "terrain_ruggedness_mean",
    "cc_mean",
    "cc_p90",
    "ch_positive_median",
    "ch_positive_fraction",
    "cbh_positive_p10",
    "cbd_p90",
    "cbd_mean",
]


def zscore_train(df, cols, train_years):
    train = df["year"].isin(train_years)
    scaler_rows = []
    for col in cols:
        mean = df.loc[train, col].mean(skipna=True)
        sd = df.loc[train, col].std(skipna=True)
        if not np.isfinite(sd) or sd == 0:
            sd = 1.0
        df[f"z_{col}"] = (df[col] - mean) / sd
        scaler_rows.append({"feature": col, "train_mean": float(mean), "train_sd": float(sd)})
    return pd.DataFrame(scaler_rows)


def add_physics_indices(df):
    dryness_terms = [
        "z_vpd_season_p95",
        "z_erc_season_p95",
        "z_bi_season_p95",
        "z_vs_season_p95",
        "z_fm100_season_p05",
        "z_fm1000_season_p05",
        "z_rmin_season_p05",
        "z_pr_season_sum",
        "z_hot_dry_windy_train_threshold_frac",
        "z_dry_spell_max_days",
    ]
    fuel_terms = [
        "z_cc_mean",
        "z_cc_p90",
        "z_ch_positive_median",
        "z_ch_positive_fraction",
        "z_cbd_mean",
        "z_slope_mean_deg",
        "z_terrain_ruggedness_mean",
    ]
    df["v2_phys_dryness_process_index"] = (
        df["z_vpd_season_p95"]
        + df["z_erc_season_p95"]
        + df["z_bi_season_p95"]
        + df["z_vs_season_p95"]
        - df["z_fm100_season_p05"]
        - df["z_fm1000_season_p05"]
        - df["z_rmin_season_p05"]
        - df["z_pr_season_sum"]
        + df["z_hot_dry_windy_train_threshold_frac"]
        + df["z_dry_spell_max_days"]
    ) / len(dryness_terms)
    df["v2_phys_fuel_structure_index"] = (
        df["z_cc_mean"]
        + df["z_cc_p90"]
        + df["z_ch_positive_median"]
        + df["z_ch_positive_fraction"]
        + df["z_cbd_mean"]
        + df["z_slope_mean_deg"]
        + df["z_terrain_ruggedness_mean"]
    ) / len(fuel_terms)
    df["v2_phys_dryness_x_fuel"] = df["v2_phys_dryness_process_index"] * df["v2_phys_fuel_structure_index"]


def main():
    require_audit_first()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()

    labels = pd.read_csv(PROJECT / config["paths"]["segment_year_labels"])
    static = pd.read_parquet(PROJECT / "data_intermediate/v2/support_aligned/static_buffer_covariates.parquet")
    temporal = pd.read_parquet(PROJECT / "data_intermediate/v2/temporal_process/segment_year_temporal_process_features.parquet")
    blocks = pd.read_parquet(PROJECT / "data_intermediate/v2/spatial_blocks/segment_spatial_blocks.parquet")

    df = labels.merge(static, on="segment_id", how="left")
    df = df.merge(temporal, on=["segment_id", "year"], how="left")
    df = df.merge(blocks, on="segment_id", how="left")

    feature_cols = [c for c in STATIC_FEATURES + DYNAMIC_FEATURES if c in df.columns]
    scaler = zscore_train(df, feature_cols, config["years"]["train"])
    add_physics_indices(df)

    df["is_train_year"] = df["year"].isin(config["years"]["train"]).astype("int8")
    df["is_holdout_year"] = df["year"].isin(config["years"]["holdout"]).astype("int8")
    df["v2_missing_dynamic_any"] = df[[c for c in DYNAMIC_FEATURES if c in df.columns]].isna().any(axis=1).astype("int8")
    df["v2_missing_static_any"] = df[[c for c in STATIC_FEATURES if c in df.columns]].isna().any(axis=1).astype("int8")

    df.to_parquet(OUT_DIR / "segment_year_v2.parquet", index=False)
    df.to_csv(OUT_DIR / "segment_year_v2.csv", index=False)
    scaler.to_csv(TABLE_DIR / "v2_train_feature_scaler.csv", index=False)

    keys_ok = int(df.duplicated(["segment_id", "year"]).sum()) == 0
    label = config["models"]["label"]
    prevalence = df.groupby("year")[label].mean().reset_index(name=f"{label}_prevalence")
    prevalence.to_csv(TABLE_DIR / "v2_label_prevalence_by_year.csv", index=False)

    summary = {
        "rows": int(len(df)),
        "unique_segments": int(df["segment_id"].nunique()),
        "years": sorted(int(x) for x in df["year"].unique()),
        "duplicate_segment_year_keys": int(df.duplicated(["segment_id", "year"]).sum()),
        "keys_ok": keys_ok,
        "train_rows": int(df["is_train_year"].sum()),
        "holdout_rows": int(df["is_holdout_year"].sum()),
        "holdout_prevalence": float(df.loc[df["is_holdout_year"] == 1, label].mean()),
        "dynamic_missing_rows": int(df["v2_missing_dynamic_any"].sum()),
        "static_missing_rows": int(df["v2_missing_static_any"].sum()),
        "model_label": label,
        "feature_scaling_rule": "means and standard deviations estimated from 2017-2021 rows only",
    }
    write_json(AUDIT_DIR / "V2_MODEL_TABLE_QA.json", summary)

    md = "# V2 Model Table QA\n\n"
    md += f"- Rows: {summary['rows']}\n"
    md += f"- Unique segments: {summary['unique_segments']}\n"
    md += f"- Years: `{summary['years']}`\n"
    md += f"- Duplicate `(segment_id, year)` keys: {summary['duplicate_segment_year_keys']}\n"
    md += f"- Train rows: {summary['train_rows']}\n"
    md += f"- Holdout rows: {summary['holdout_rows']}\n"
    md += f"- Holdout prevalence for `{label}`: {summary['holdout_prevalence']:.6f}\n"
    md += f"- Rows with any missing dynamic feature: {summary['dynamic_missing_rows']}\n"
    md += f"- Rows with any missing static feature: {summary['static_missing_rows']}\n"
    md += "- Feature scaling: 2017-2021 train rows only.\n\n"
    md += "## Label Prevalence by Year\n\n"
    md += prevalence.to_markdown(index=False)
    md += "\n"
    write_text(AUDIT_DIR / "V2_MODEL_TABLE_QA.md", md)
    print(f"[done] {OUT_DIR / 'segment_year_v2.parquet'}")


if __name__ == "__main__":
    main()
