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
from matplotlib.patches import FancyArrowPatch, Rectangle


PHASE1 = PROJECT / "data/processed/phase1"
PHASE6 = PROJECT / "data/processed/phase6"
FIG_DIR = PROJECT / "outputs/figures/phase8"

COLORS = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "grid": "#d8d5cd",
    "context": "#d8d3ca",
    "context_dark": "#8c887f",
    "teal": "#005f73",
    "gold": "#c27a15",
    "green": "#3d6b35",
    "steel": "#4f6d7a",
    "muted": "#918b80",
}

CMAP_DECISION = LinearSegmentedColormap.from_list(
    "decision_teal_gold",
    ["#f1eee6", "#c8d7ce", "#72a6a6", "#0b7285", "#c27a15"],
)


def load_segment_decision_gdf():
    segments = gpd.read_file(PHASE1 / "segments_1km.gpkg")[["segment_id", "geometry"]]
    stan = pd.read_parquet(PHASE6 / "stan_mcmc_pilot/phase6_stan_segment_posterior_decision_metrics.parquet")
    gdf = segments.merge(stan, on="segment_id", how="inner")
    return gdf.to_crs(3310)


def style_map(ax, title, subtitle=None):
    ax.set_facecolor(COLORS["paper"])
    ax.set_axis_off()
    ax.set_title(title, loc="left", fontsize=9.6, color=COLORS["text"], pad=8)
    if subtitle:
        ax.text(0, 1.01, subtitle, transform=ax.transAxes, fontsize=7.5, color=COLORS["axis"], va="bottom")


def set_bounds(ax, bounds, pad=0.035):
    xmin, ymin, xmax, ymax = bounds
    dx = xmax - xmin
    dy = ymax - ymin
    ax.set_xlim(xmin - dx * pad, xmax + dx * pad)
    ax.set_ylim(ymin - dy * pad, ymax + dy * pad)


def zoom_bounds(gdf):
    high = gdf.sort_values("p_rank_in_top10", ascending=False).head(max(120, int(0.015 * len(gdf))))
    centroids = high.geometry.centroid
    cx = float(centroids.x.median())
    cy = float(centroids.y.median())
    half_w = 52000.0
    half_h = 62000.0
    return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def plot_faceted_zoom_maps():
    gdf = load_segment_decision_gdf()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    metrics = [
        ("posterior_mean_exposure_probability", "Posterior mean", "Expected holdout exposure probability", 0.0, 0.12),
        ("p_exposure_gt_tau", "Exceedance probability", "P(segment exposure > training prevalence)", 0.0, 1.0),
        ("p_rank_in_top10", "Top-decile rank probability", "P(segment enters top 10% under posterior draws)", 0.0, 1.0),
    ]
    full_bounds = gdf.total_bounds
    z_bounds = zoom_bounds(gdf)

    fig, axes = plt.subplots(2, 3, figsize=(13.6, 8.3), facecolor=COLORS["paper"])
    for row, bounds, row_label in [(0, full_bounds, "Full study region"), (1, z_bounds, "Zoomed high-rank corridor")]:
        for col, (metric, title, subtitle, vmin, vmax) in enumerate(metrics):
            ax = axes[row, col]
            gdf.plot(ax=ax, color=COLORS["context"], linewidth=0.18 if row == 0 else 0.30, alpha=0.42)
            active = gdf[gdf[metric] > 0]
            active.plot(
                ax=ax,
                column=metric,
                cmap=CMAP_DECISION,
                linewidth=0.82 if row == 0 else 1.25,
                alpha=0.96,
                vmin=vmin,
                vmax=vmax,
                legend=(col == 2),
                legend_kwds={"shrink": 0.65, "pad": 0.01, "label": "posterior probability"},
            )
            set_bounds(ax, bounds)
            style_map(ax, title if row == 0 else f"Zoom: {title}", subtitle if row == 0 else row_label)
            if row == 0 and col == 0:
                zxmin, zymin, zxmax, zymax = z_bounds
                rect = Rectangle((zxmin, zymin), zxmax - zxmin, zymax - zymin, fill=False, lw=1.2, ec=COLORS["gold"])
                ax.add_patch(rect)

    fig.suptitle(
        "Posterior wildfire exposure decisions: full region and zoomed high-rank corridor",
        fontsize=13,
        color=COLORS["text"],
        y=0.97,
    )
    fig.subplots_adjust(left=0.02, right=0.965, bottom=0.035, top=0.88, wspace=0.08, hspace=0.18)
    out = FIG_DIR / "phase8_faceted_zoom_posterior_maps.png"
    fig.savefig(out, dpi=320, facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def plot_research_advantage_matrix():
    methods = ["Deterministic\nscore", "Tree ML\nbaseline", "Bayesian\nranking", "Stan MCMC\nposterior"]
    criteria = [
        "Public-data\nreproducible",
        "Physics\ninterpretability",
        "Temporal-holdout\nvalidated",
        "Probability\ncalibration",
        "Posterior\nuncertainty",
        "Rank decision\nprobability",
        "Ignition-causality\nboundary",
    ]
    score = np.array(
        [
            [1.0, 1.0, 1.0, 0.45, 0.0, 0.0, 0.75],
            [1.0, 0.35, 1.0, 0.45, 0.0, 0.0, 0.75],
            [1.0, 0.9, 1.0, 0.85, 0.85, 1.0, 1.0],
            [1.0, 0.9, 1.0, 0.9, 1.0, 1.0, 1.0],
        ]
    )
    cmap = LinearSegmentedColormap.from_list("advantage", ["#ece8dd", "#9fb9ae", COLORS["teal"]])
    fig, ax = plt.subplots(figsize=(10.6, 4.7), facecolor=COLORS["paper"], constrained_layout=True)
    im = ax.imshow(score, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(criteria)), criteria, fontsize=8)
    ax.set_yticks(range(len(methods)), methods, fontsize=9)
    ax.tick_params(axis="x", rotation=0, colors=COLORS["axis"])
    ax.tick_params(axis="y", colors=COLORS["axis"])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Research advantage relative to common risk-scoring baselines", loc="left", fontsize=12, color=COLORS["text"], pad=16)
    ax.text(0, 1.03, "Darker cells indicate stronger support for the criterion in this study design.", transform=ax.transAxes, fontsize=8, color=COLORS["axis"])
    for i in range(score.shape[0]):
        for j in range(score.shape[1]):
            label = "high" if score[i, j] >= 0.8 else ("partial" if score[i, j] > 0 else "none")
            ax.text(j, i, label, ha="center", va="center", fontsize=7.5, color="white" if score[i, j] > 0.65 else COLORS["text"])
    cbar = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
    cbar.set_label("support level", color=COLORS["axis"])
    cbar.ax.tick_params(colors=COLORS["axis"])
    out = FIG_DIR / "phase8_research_advantage_matrix.png"
    fig.savefig(out, dpi=320, facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def draw_box(ax, xy, wh, title, body, face="#f1eee6", edge=COLORS["teal"]):
    x, y = xy
    w, h = wh
    rect = Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, lw=1.25)
    ax.add_patch(rect)
    ax.text(x + 0.03 * w, y + h - 0.20 * h, title, fontsize=10, weight="bold", color=COLORS["text"], va="top")
    ax.text(x + 0.03 * w, y + h - 0.43 * h, body, fontsize=8.1, color=COLORS["axis"], va="top", linespacing=1.25)


def arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, lw=1.1, color=COLORS["muted"]))


def plot_bayesian_method_schematic():
    fig, ax = plt.subplots(figsize=(12.4, 5.6), facecolor=COLORS["paper"])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    draw_box(ax, (0.03, 0.56), (0.22, 0.28), "Public data", "Transmission lines\nFire perimeters + causes\ngridMET, DEM, LANDFIRE", face="#f4f1e8")
    draw_box(ax, (0.30, 0.56), (0.22, 0.28), "Segment-year panel", "1 km line segments\n2017-2023 annual labels\nCAUSE=11 excluded from y_exo", face="#f4f1e8")
    draw_box(ax, (0.57, 0.56), (0.18, 0.28), "Bayesian model", "Regularized logistic model\nTraining-period fit\nPosterior approximation", face="#e7f0ed")
    draw_box(ax, (0.80, 0.56), (0.17, 0.28), "Posterior draws", "Annual probability\nSegment aggregation\nRank per draw", face="#e7f0ed")
    draw_box(
        ax,
        (0.16, 0.08),
        (0.34, 0.31),
        "Decision quantities",
        "Posterior exceedance\nq_i\n"
        "Posterior top-decile membership\nrho_i\n"
        "Rank uncertainty across draws",
        face="#f0eadb",
        edge=COLORS["gold"],
    )
    draw_box(ax, (0.50, 0.12), (0.30, 0.25), "Validation", "Temporal holdout: 2022-2023\nROC-AUC, PR-AUC, Brier\nTop-decile capture", face="#f0eadb", edge=COLORS["gold"])
    arrow(ax, (0.25, 0.70), (0.30, 0.70))
    arrow(ax, (0.52, 0.70), (0.57, 0.70))
    arrow(ax, (0.75, 0.70), (0.80, 0.70))
    arrow(ax, (0.88, 0.56), (0.43, 0.32))
    arrow(ax, (0.43, 0.245), (0.50, 0.245))
    ax.text(0.03, 0.94, "Posterior exposure and posterior top-decile rank probabilities", fontsize=13, color=COLORS["text"], weight="bold")
    ax.text(0.03, 0.90, "The asset is a receptor interface; the posterior ranks external wildfire exposure, not line-caused ignition.", fontsize=8.7, color=COLORS["axis"])
    out = FIG_DIR / "phase8_bayesian_method_schematic.png"
    fig.savefig(out, dpi=320, facecolor=COLORS["paper"])
    fig.savefig(FIG_DIR / "phase8_bayesian_method_schematic-2.png", dpi=320, facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [
        plot_faceted_zoom_maps(),
        plot_research_advantage_matrix(),
        plot_bayesian_method_schematic(),
    ]
    for out in outputs:
        print(out)


if __name__ == "__main__":
    main()
