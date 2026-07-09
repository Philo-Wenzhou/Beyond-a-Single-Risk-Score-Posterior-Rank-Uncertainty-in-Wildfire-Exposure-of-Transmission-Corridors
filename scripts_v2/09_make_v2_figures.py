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
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

from utils_v2 import PROJECT, load_config, require_audit_first, write_text


FIG_DIR = PROJECT / "outputs/v2/figures"
AUDIT_DIR = PROJECT / "outputs/v2/audit"

MODEL_LABELS = {
    "M_A_physics_score": "M-A physics score",
    "M_B_logistic_l2": "M-B L2 logistic",
    "M_C_logistic_l2_block_year": "M-C L2 + block/year",
}

METRIC_LABELS = {
    "roc_auc": "ROC-AUC",
    "pr_auc": "PR-AUC",
    "top_decile_precision": "Top-decile precision",
    "delta_roc_auc": "Delta ROC-AUC",
    "delta_pr_auc": "Delta PR-AUC",
    "delta_top_decile_precision": "Delta top-decile precision",
}


def style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.7,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.dpi": 150,
            "savefig.dpi": 300,
        }
    )


def save(fig, path, write_pdf=True):
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    if write_pdf:
        fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def holdout_metrics():
    metrics = pd.read_csv(PROJECT / "outputs/v2/tables/v2_holdout_validation_metrics.csv")
    metrics["model_label"] = metrics["model"].map(MODEL_LABELS)
    metrics = metrics.set_index("model").loc[list(MODEL_LABELS)].reset_index()
    long = metrics.melt(
        id_vars=["model", "model_label", "prevalence"],
        value_vars=["roc_auc", "pr_auc", "top_decile_precision"],
        var_name="metric",
        value_name="value",
    )
    metric_order = ["roc_auc", "pr_auc", "top_decile_precision"]
    colors = {"roc_auc": "#4C78A8", "pr_auc": "#5A8F5B", "top_decile_precision": "#7F7F7F"}
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.35), sharey=True)
    for ax, metric in zip(axes, metric_order):
        sub = long[long["metric"].eq(metric)].copy()
        y = np.arange(len(sub))
        ax.barh(y, sub["value"], color=colors[metric], height=0.52)
        for yi, value in zip(y, sub["value"]):
            ax.text(value, yi, f" {value:.3f}", va="center", ha="left", fontsize=7, color="#222222")
        ax.set_yticks(y)
        ax.set_yticklabels(sub["model_label"] if ax is axes[0] else [])
        ax.invert_yaxis()
        ax.set_title(METRIC_LABELS[metric], fontsize=8.5, pad=5)
        ax.grid(axis="x", color="#E2E2E2", linewidth=0.55)
        ax.set_xlabel("Holdout value", labelpad=3)
        ax.margins(x=0.18)
        if metric == "pr_auc":
            ax.axvline(metrics["prevalence"].iloc[0], color="#333333", linestyle="--", linewidth=0.8)
            ax.text(
                metrics["prevalence"].iloc[0],
                -0.55,
                "prevalence",
                ha="center",
                va="bottom",
                fontsize=6.5,
                color="#333333",
            )
    return fig


def bootstrap_intervals():
    boot = pd.read_csv(PROJECT / "outputs/v2/tables/v2_block_bootstrap_metric_differences.csv")
    boot["model_label"] = boot["comparison"].str.replace(" minus M_A_physics_score", "", regex=False).map(MODEL_LABELS)
    boot["metric_label"] = boot["metric"].map(METRIC_LABELS)
    boot["plot_label"] = boot["model_label"] + "\n" + boot["metric_label"].str.replace("Delta ", "")
    fig, ax = plt.subplots(figsize=(5.9, 3.35))
    y = np.arange(len(boot))
    xerr = np.vstack([boot["mean"] - boot["ci025"], boot["ci975"] - boot["mean"]])
    colors = boot["model_label"].map({"M-B L2 logistic": "#4C78A8", "M-C L2 + block/year": "#5A8F5B"}).fillna("#4C78A8")
    for yi, row, color in zip(y, boot.itertuples(index=False), colors):
        ax.errorbar(row.mean, yi, xerr=[[row.mean - row.ci025], [row.ci975 - row.mean]], fmt="o", color=color, ecolor="#8C8C8C", capsize=2.5, markersize=3.8)
    ax.axvline(0, color="#333333", linewidth=0.8, linestyle="--")
    ax.set_yticks(y)
    ax.set_yticklabels(boot["plot_label"])
    ax.invert_yaxis()
    ax.set_xlabel("Metric difference vs M-A")
    ax.grid(axis="x", color="#E2E2E2", linewidth=0.55)
    ax.set_title("50 km block-bootstrap differences", pad=5)
    return fig


def rank_stability_heatmap():
    tab = pd.read_csv(PROJECT / "outputs/v2/tables/v2_pairwise_rank_stability.csv")
    pivot = tab.pivot_table(index=["model_a", "model_b"], columns="year", values="top_decile_jaccard")
    fig, ax = plt.subplots(figsize=(4.9, 2.75))
    im = ax.imshow(pivot.values, cmap="YlGnBu", vmin=0, vmax=max(0.5, np.nanmax(pivot.values)))
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns.astype(str))
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels([f"{MODEL_LABELS[a]}\nvs {MODEL_LABELS[b]}" for a, b in pivot.index], fontsize=7.2)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, f"{pivot.values[i, j]:.2f}", ha="center", va="center", fontsize=7.5, color="#111111")
    ax.set_title("Top-decile Jaccard overlap", pad=5)
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Jaccard")
    return fig


def holdout_score_map(config):
    seg = gpd.read_file(PROJECT / config["paths"]["segments_1km"])
    if seg.crs is None:
        seg = seg.set_crs("EPSG:4326")
    seg = seg.to_crs(config["spatial"]["project_crs"])
    pred = pd.read_parquet(PROJECT / "data_model/v2/fits/model_ladder_predictions.parquet")
    holdout = pred[pred["is_holdout_year"].eq(1)].groupby("segment_id", as_index=False)[
        ["M_A_physics_score", "M_C_logistic_l2_block_year_prob"]
    ].mean()
    g = seg.merge(holdout, on="segment_id", how="left")
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 5.2))
    for ax, col, title in [
        (axes[0], "M_A_physics_score", "M-A physics score"),
        (axes[1], "M_C_logistic_l2_block_year_prob", "M-C logistic probability"),
    ]:
        g.plot(ax=ax, color="#D9D9D9", linewidth=0.15)
        g.dropna(subset=[col]).plot(ax=ax, column=col, cmap="viridis", linewidth=0.35, legend=True)
        ax.set_title(title)
        ax.set_axis_off()
        ax.set_aspect("equal")
    fig.suptitle("Holdout mean external wildfire exposure ranking scores", y=0.98, fontsize=10)
    return fig


def hillshade(elev, azimuth=315, altitude=45):
    arr = elev.astype("float64")
    gy, gx = np.gradient(arr)
    slope = np.pi / 2.0 - np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az = np.deg2rad(azimuth)
    alt = np.deg2rad(altitude)
    shade = np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect)
    return np.clip((shade + 1) / 2, 0, 1)


def read_dem_hillshade(config):
    dem_path = PROJECT / config["paths"]["dem"]
    with rasterio.open(dem_path) as src:
        with WarpedVRT(
            src,
            crs=config["spatial"]["project_crs"],
            resolution=500.0,
            resampling=Resampling.bilinear,
            nodata=np.nan,
        ) as vrt:
            elev = vrt.read(1, masked=True).filled(np.nan)
            valid = np.isfinite(elev)
            transform = vrt.transform
            left, bottom, right, top = rasterio.transform.array_bounds(vrt.height, vrt.width, transform)
    fill = np.nanmedian(elev[valid]) if valid.any() else 0.0
    elev = np.where(valid, elev, fill)
    return hillshade(elev), valid.astype("float32"), (left, right, bottom, top)


def context_hillshade_map(config):
    seg = gpd.read_file(PROJECT / config["paths"]["segments_1km"])
    if seg.crs is None:
        seg = seg.set_crs("EPSG:4326")
    seg = seg.to_crs(config["spatial"]["project_crs"])
    pred = pd.read_parquet(PROJECT / "data_model/v2/fits/model_ladder_predictions.parquet")
    holdout = pred[pred["is_holdout_year"].eq(1)].groupby("segment_id", as_index=False)["M_A_physics_score"].mean()
    g = seg.merge(holdout, on="segment_id", how="left")

    shade, valid, extent = read_dem_hillshade(config)
    county_zip = PROJECT / "data/raw/census/tl_2024_us_county.zip"
    counties = gpd.read_file(f"zip://{county_zip}").query("STATEFP == '06'").to_crs(config["spatial"]["project_crs"])
    xmin, ymin, xmax, ymax = seg.total_bounds
    pad_x = (xmax - xmin) * 0.06
    pad_y = (ymax - ymin) * 0.06
    counties = counties.cx[xmin - pad_x : xmax + pad_x, ymin - pad_y : ymax + pad_y]

    fig, ax = plt.subplots(figsize=(5.6, 7.0))
    ax.imshow(shade, extent=extent, cmap="Greys", alpha=valid * 0.40, origin="upper")
    counties.boundary.plot(ax=ax, color="#FFFFFF", linewidth=1.0, alpha=0.78)
    counties.boundary.plot(ax=ax, color="#777777", linewidth=0.35, alpha=0.75)
    g.plot(ax=ax, color="#BDBDBD", linewidth=0.18, alpha=0.60)
    g.dropna(subset=["M_A_physics_score"]).plot(
        ax=ax,
        column="M_A_physics_score",
        cmap="viridis",
        linewidth=0.42,
        legend=True,
        legend_kwds={"label": "Mean holdout M-A score", "shrink": 0.62},
    )
    ax.set_xlim(xmin - pad_x, xmax + pad_x)
    ax.set_ylim(ymin - pad_y, ymax + pad_y)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("Northern Sierra / Southern Cascades transmission-line exposure context", fontsize=9, pad=6)
    return fig


def main():
    require_audit_first()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    style()
    config = load_config()
    figures = [
        ("v2_holdout_metrics", "v2_holdout_metrics.png", holdout_metrics, "outputs/v2/tables/v2_holdout_validation_metrics.csv", "Holdout validation metrics"),
        ("v2_block_bootstrap", "v2_block_bootstrap_differences.png", bootstrap_intervals, "outputs/v2/tables/v2_block_bootstrap_metric_differences.csv", "Paired block-bootstrap differences"),
        ("v2_rank_stability", "v2_top_decile_jaccard_heatmap.png", rank_stability_heatmap, "outputs/v2/tables/v2_pairwise_rank_stability.csv", "Top-decile rank-set stability"),
        ("v2_holdout_score_map", "v2_holdout_score_map.png", lambda: holdout_score_map(config), "data_model/v2/fits/model_ladder_predictions.parquet", "Holdout mean score maps"),
        ("v2_context_hillshade_map", "v2_context_hillshade_map.png", lambda: context_hillshade_map(config), "data/raw/census/tl_2024_us_county.zip; data/raw/dem_3dep/usgs_3dep_dem_study_area_2048.tif; data_model/v2/fits/model_ladder_predictions.parquet", "Hillshade and county-boundary context map"),
    ]
    rows = []
    for fig_id, filename, fn, source, caption in figures:
        print(f"[figure] {fig_id}", flush=True)
        fig = fn()
        path = FIG_DIR / filename
        save(fig, path, write_pdf=not fig_id.endswith("_map"))
        rows.append(
            {
                "figure_id": fig_id,
                "file": f"outputs/v2/figures/{filename}",
                "script": "scripts_v2/09_make_v2_figures.py",
                "source_table": source,
                "manuscript_section": "Results",
                "caption_short": caption,
                "status": "complete",
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(FIG_DIR / "FIGURE_MANIFEST.csv", index=False)
    write_text(AUDIT_DIR / "V2_FIGURES_QA.md", "# V2 Figures QA\n\nGenerated V2 result figures listed in `outputs/v2/figures/FIGURE_MANIFEST.csv`.\n")
    print(f"[done] {FIG_DIR / 'FIGURE_MANIFEST.csv'}")


if __name__ == "__main__":
    main()
