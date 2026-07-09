import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle


PHASE1 = PROJECT / "data/processed/phase1"
PHASE3 = PROJECT / "data/processed/phase3"
PHASE4 = PROJECT / "data/processed/phase4"
FIG_DIR = PROJECT / "outputs/figures/phase10"
TABLE_DIR = PROJECT / "outputs/tables"

TEST_YEARS = [2022, 2023]
LABEL = "exogenous_fire_exposure"

COLORS = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "context": "#d8d3ca",
    "teal": "#005f73",
    "gold": "#c27a15",
}

CMAP_DECISION = LinearSegmentedColormap.from_list(
    "decision_teal_gold",
    ["#f2efe8", "#d2ded6", "#8cb9b3", "#168198", "#c27a15"],
)


def ensure_dirs():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def load_segment_metrics():
    metrics = pd.read_parquet(PHASE4 / "phase4_segment_posterior_decision_metrics.parquet")
    panel = pd.read_parquet(PHASE3 / "segment_year_model_table.parquet")
    holdout = (
        panel.loc[panel["year"].isin(TEST_YEARS)]
        .groupby("segment_id", as_index=False)[LABEL]
        .max()
        .rename(columns={LABEL: "observed_holdout_exposure"})
    )
    return metrics.merge(holdout, on="segment_id", how="left").fillna({"observed_holdout_exposure": 0})


def build_rank_uncertainty_tables(metrics):
    work = metrics.copy()
    rho = work["p_rank_top10"]
    work["posterior_rank_group"] = np.select(
        [rho >= 0.9, rho > 0.1],
        ["Stable top-decile (rho >= 0.9)", "Rank-uncertain (0.1 < rho < 0.9)"],
        default="Stable lower rank (rho <= 0.1)",
    )
    order = [
        "Stable top-decile (rho >= 0.9)",
        "Rank-uncertain (0.1 < rho < 0.9)",
        "Stable lower rank (rho <= 0.1)",
    ]
    summary = (
        work.groupby("posterior_rank_group", as_index=False)
        .agg(
            segments=("segment_id", "count"),
            observed_exposed_segments=("observed_holdout_exposure", "sum"),
            exposure_frequency=("observed_holdout_exposure", "mean"),
            mean_posterior_rank_probability=("p_rank_top10", "mean"),
            mean_posterior_exposure_probability=("posterior_mean_exposure_prob", "mean"),
        )
        .set_index("posterior_rank_group")
        .reindex(order)
        .reset_index()
    )
    summary["observed_exposed_segments"] = summary["observed_exposed_segments"].astype(int)
    summary.to_csv(TABLE_DIR / "phase10_posterior_rank_uncertainty_groups.csv", index=False)

    n = len(work)
    k = int(np.ceil(0.1 * n))
    point_top = set(work.nlargest(k, "posterior_mean_exposure_prob")["segment_id"])
    stable_top = set(work.loc[work["p_rank_top10"] >= 0.9, "segment_id"])
    intersection = point_top & stable_top
    union = point_top | stable_top
    point = work.loc[work["segment_id"].isin(point_top)].copy()
    overlap = pd.DataFrame(
        [
            {
                "n_segments": n,
                "top_decile_k": k,
                "point_top_decile_size": len(point_top),
                "stable_top_decile_size": len(stable_top),
                "intersection_size": len(intersection),
                "jaccard": len(intersection) / len(union) if union else np.nan,
                "point_top_with_rho_lt_0_5": int((point["p_rank_top10"] < 0.5).sum()),
                "point_top_with_rho_lt_0_5_fraction": float((point["p_rank_top10"] < 0.5).mean()),
            }
        ]
    )
    overlap.to_csv(TABLE_DIR / "phase10_point_vs_posterior_top_decile_overlap.csv", index=False)

    payload = {
        "rank_uncertainty_groups": summary.to_dict(orient="records"),
        "point_vs_posterior_top_decile": overlap.iloc[0].to_dict(),
    }
    (TABLE_DIR / "phase10_rank_uncertainty_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return summary, overlap


def load_decision_gdf(metrics):
    segments = gpd.read_file(PHASE1 / "segments_1km.gpkg")[["segment_id", "geometry"]]
    return segments.merge(metrics, on="segment_id", how="inner").to_crs(3310)


def set_bounds(ax, bounds, pad=0.035):
    xmin, ymin, xmax, ymax = bounds
    dx = xmax - xmin
    dy = ymax - ymin
    ax.set_xlim(xmin - dx * pad, xmax + dx * pad)
    ax.set_ylim(ymin - dy * pad, ymax + dy * pad)


def zoom_bounds(gdf):
    high = gdf.sort_values("p_rank_top10", ascending=False).head(max(160, int(0.02 * len(gdf))))
    centroids = high.geometry.centroid
    cx = float(centroids.x.median())
    cy = float(centroids.y.median())
    half_w = 56000.0
    half_h = 66000.0
    return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def plot_maps(gdf, bounds, out_path, title, show_zoom_box=False, z_bounds=None):
    metrics = [
        ("posterior_mean_exposure_prob", "A. Posterior mean exposure", "mean probability", 0.0, 0.12),
        ("p_exposure_gt_threshold", "B. Exceedance probability", "q_i", 0.0, 1.0),
        ("p_rank_top10", "C. Top-decile rank probability", "rho_i", 0.0, 1.0),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.55), facecolor=COLORS["paper"])
    for ax, (col, panel_title, cbar_label, vmin, vmax) in zip(axes, metrics):
        gdf.plot(ax=ax, color=COLORS["context"], linewidth=0.23, alpha=0.55)
        active = gdf[gdf[col] > 0]
        active.plot(
            ax=ax,
            column=col,
            cmap=CMAP_DECISION,
            linewidth=0.82,
            alpha=0.96,
            vmin=vmin,
            vmax=vmax,
            legend=True,
            legend_kwds={"shrink": 0.74, "pad": 0.01, "label": cbar_label},
        )
        if show_zoom_box and z_bounds is not None:
            zxmin, zymin, zxmax, zymax = z_bounds
            ax.add_patch(
                Rectangle((zxmin, zymin), zxmax - zxmin, zymax - zymin, fill=False, lw=1.15, ec=COLORS["gold"])
            )
        set_bounds(ax, bounds)
        ax.set_title(panel_title, loc="left", fontsize=9.8, color=COLORS["text"], pad=8)
        ax.set_axis_off()
        ax.set_facecolor(COLORS["paper"])
    fig.suptitle(title, fontsize=12.5, color=COLORS["text"], y=0.985)
    fig.subplots_adjust(left=0.018, right=0.982, bottom=0.03, top=0.86, wspace=0.10)
    fig.savefig(out_path, dpi=320, facecolor=COLORS["paper"])
    plt.close(fig)


def build_posterior_maps(metrics):
    gdf = load_decision_gdf(metrics)
    full_bounds = gdf.total_bounds
    z_bounds = zoom_bounds(gdf)
    full_out = FIG_DIR / "phase10_posterior_decision_maps_full_region.png"
    zoom_out = FIG_DIR / "phase10_posterior_decision_maps_zoom_corridor.png"
    plot_maps(
        gdf,
        full_bounds,
        full_out,
        "Posterior external wildfire exposure decisions, full study region",
        show_zoom_box=True,
        z_bounds=z_bounds,
    )
    plot_maps(gdf, z_bounds, zoom_out, "Posterior external wildfire exposure decisions, high-rank corridor")
    return full_out, zoom_out


def main():
    ensure_dirs()
    metrics = load_segment_metrics()
    summary, overlap = build_rank_uncertainty_tables(metrics)
    maps = build_posterior_maps(metrics)
    print(summary.to_string(index=False))
    print(overlap.to_string(index=False))
    for out in maps:
        print(out)


if __name__ == "__main__":
    main()
