import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap


PHASE1 = PROJECT / "data/processed/phase1"
PHASE6 = PROJECT / "data/processed/phase6"
FIG_DIR = PROJECT / "outputs/figures/phase6"

COLORS = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "context": "#d7d2c8",
    "context_dark": "#918b80",
}

CMAP_TEAL_GOLD = LinearSegmentedColormap.from_list(
    "teal_gold",
    ["#ece8dd", "#9fb9ae", "#3f8790", "#005f73", "#c27a15"],
)


def style_map(ax, title, subtitle):
    ax.set_title(title, loc="left", fontsize=10.5, color=COLORS["text"], pad=16)
    ax.text(0, 1.012, subtitle, transform=ax.transAxes, fontsize=8, color=COLORS["axis"], va="bottom")
    ax.set_axis_off()
    ax.set_facecolor(COLORS["paper"])


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    segments = gpd.read_file(PHASE1 / "segments_1km.gpkg")[["segment_id", "geometry"]]
    metrics = pd.read_parquet(PHASE6 / "stan_mcmc_pilot/phase6_stan_segment_posterior_decision_metrics.parquet")
    gdf = segments.merge(metrics, on="segment_id", how="inner")
    if gdf.crs and gdf.crs.to_epsg() != 3310:
        gdf = gdf.to_crs(3310)

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 7.2), facecolor=COLORS["paper"])
    columns = [
        ("p_exposure_gt_tau", "Posterior exceedance probability", "P(segment exposure probability > training prevalence)"),
        ("p_rank_in_top10", "Posterior top-decile rank probability", "P(segment enters top 10% under MCMC draws)"),
    ]
    for ax, (col, title, subtitle) in zip(axes, columns):
        gdf.plot(ax=ax, color=COLORS["context"], linewidth=0.23, alpha=0.44)
        gdf[gdf[col] > 0].plot(
            ax=ax,
            column=col,
            cmap=CMAP_TEAL_GOLD,
            linewidth=0.92,
            alpha=0.96,
            legend=True,
            legend_kwds={"shrink": 0.58, "pad": 0.01, "label": "posterior probability"},
        )
        style_map(ax, title, subtitle)
        xmin, ymin, xmax, ymax = gdf.total_bounds
        pad_x = (xmax - xmin) * 0.04
        pad_y = (ymax - ymin) * 0.04
        ax.set_xlim(xmin - pad_x, xmax + pad_x)
        ax.set_ylim(ymin - pad_y, ymax + pad_y)

    fig.suptitle("Stan MCMC posterior decision metrics for transmission-line exposure", fontsize=12, color=COLORS["text"], y=0.965)
    fig.subplots_adjust(left=0.025, right=0.965, bottom=0.035, top=0.86, wspace=0.13)
    out = FIG_DIR / "phase6_stan_mcmc_decision_maps.png"
    fig.savefig(out, dpi=300, facecolor=COLORS["paper"])
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
