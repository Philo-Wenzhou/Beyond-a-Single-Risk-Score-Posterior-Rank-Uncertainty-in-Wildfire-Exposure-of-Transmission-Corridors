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
PHASE3 = PROJECT / "data/processed/phase3"
FIG_DIR = PROJECT / "outputs/figures/phase8"

COLORS = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "context": "#d8d3ca",
}

CMAP_DRY = LinearSegmentedColormap.from_list("dry_teal_gold", ["#e9e4d8", "#8fb7b3", "#006d77", "#c27a15"])
CMAP_TERRAIN = LinearSegmentedColormap.from_list("terrain_quiet", ["#ece8dd", "#b7c8b2", "#718c76", "#5a5f54"])
CMAP_FUEL = LinearSegmentedColormap.from_list("fuel_quiet", ["#efece3", "#bed0bc", "#6e996b", "#2f5f3a"])


def load_covariate_gdf(year=2021):
    segments = gpd.read_file(PHASE1 / "segments_1km.gpkg")[["segment_id", "geometry"]]
    table = pd.read_parquet(PHASE3 / "segment_year_model_table.parquet")
    cols = [
        "segment_id",
        "year",
        "gridmet_vpd_p95",
        "gridmet_fm100_p05",
        "dem_elevation_m",
        "landfire_canopy_cover_pct",
        "landfire_canopy_height_m",
    ]
    cov = table.loc[table["year"] == year, cols].copy()
    cov["landfire_canopy_height_decoded_m"] = cov["landfire_canopy_height_m"] / 10.0
    gdf = segments.merge(cov, on="segment_id", how="inner")
    return gdf.to_crs(3310)


def style_ax(ax, title, subtitle=None):
    ax.set_facecolor(COLORS["paper"])
    ax.set_axis_off()
    ax.text(0, 1.075, title, transform=ax.transAxes, fontsize=10.2, color=COLORS["text"], va="bottom")
    if subtitle:
        ax.text(0, 1.035, subtitle, transform=ax.transAxes, fontsize=8, color=COLORS["axis"], va="bottom")


def plot_layer(ax, gdf, column, title, subtitle, cmap, label, vmin=None, vmax=None, linewidth=0.70):
    gdf.plot(ax=ax, color=COLORS["context"], linewidth=0.20, alpha=0.35)
    gdf.plot(
        ax=ax,
        column=column,
        cmap=cmap,
        linewidth=linewidth,
        alpha=0.95,
        vmin=vmin,
        vmax=vmax,
        legend=True,
        legend_kwds={"shrink": 0.62, "pad": 0.01, "label": label},
    )
    style_ax(ax, title, subtitle)


def save_combined(gdf):
    fig = plt.figure(figsize=(11.4, 12.2), facecolor=COLORS["paper"])
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1.05, 1], hspace=0.30, wspace=0.12)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, :])
    ax4 = fig.add_subplot(gs[2, 0])
    ax5 = fig.add_subplot(gs[2, 1])

    plot_layer(ax1, gdf, "gridmet_vpd_p95", "gridMET VPD p95", "Atmospheric drying demand, 2021", CMAP_DRY, "kPa", vmin=1.5, vmax=4.5)
    plot_layer(ax2, gdf, "gridmet_fm100_p05", "gridMET 100-h fuel moisture p05", "Lower values indicate drier dead fuels, 2021", CMAP_DRY.reversed(), "%", vmin=3.5, vmax=9.0)
    plot_layer(ax3, gdf, "dem_elevation_m", "USGS 3DEP elevation", "Terrain context sampled to transmission-line segments", CMAP_TERRAIN, "m", vmin=0, vmax=2200, linewidth=0.82)
    plot_layer(ax4, gdf, "landfire_canopy_cover_pct", "LANDFIRE canopy cover", "Fuel-structure context near each segment", CMAP_FUEL, "%", vmin=0, vmax=75)
    plot_layer(ax5, gdf, "landfire_canopy_height_decoded_m", "LANDFIRE canopy height", "Fuel-structure context near each segment", CMAP_FUEL, "decoded m", vmin=0, vmax=40)

    fig.suptitle("Model-aligned public environmental covariates", fontsize=13, color=COLORS["text"], y=0.975)
    fig.text(
        0.02,
        0.946,
        "Maps show segment-level covariate summaries used by the exposure model, replacing raw multi-panel download previews.",
        fontsize=8.8,
        color=COLORS["axis"],
    )
    out = FIG_DIR / "phase8_model_aligned_environmental_covariates.png"
    fig.savefig(out, dpi=320, facecolor=COLORS["paper"], bbox_inches="tight")
    plt.close(fig)
    return out


def save_pair(gdf, filename, specs, size=(10.8, 5.2)):
    fig, axes = plt.subplots(1, len(specs), figsize=size, facecolor=COLORS["paper"], constrained_layout=True)
    if len(specs) == 1:
        axes = [axes]
    for ax, spec in zip(axes, specs):
        plot_layer(ax, gdf, *spec)
    out = FIG_DIR / filename
    fig.savefig(out, dpi=320, facecolor=COLORS["paper"], bbox_inches="tight")
    plt.close(fig)
    return out


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    gdf = load_covariate_gdf(year=2021)
    outputs = [
        save_combined(gdf),
        save_pair(
            gdf,
            "phase8_gridmet_model_covariates_2021.png",
            [
                ("gridmet_vpd_p95", "gridMET VPD p95", "Atmospheric drying demand, 2021", CMAP_DRY, "kPa", 1.5, 4.5, 0.72),
                ("gridmet_fm100_p05", "gridMET 100-h fuel moisture p05", "Lower values indicate drier dead fuels, 2021", CMAP_DRY.reversed(), "%", 3.5, 9.0, 0.72),
            ],
        ),
        save_pair(
            gdf,
            "phase8_dem_model_covariate.png",
            [("dem_elevation_m", "USGS 3DEP elevation", "Terrain context sampled to line segments", CMAP_TERRAIN, "m", 0, 2200, 0.82)],
            size=(8.8, 5.6),
        ),
        save_pair(
            gdf,
            "phase8_landfire_model_covariates.png",
            [
                ("landfire_canopy_cover_pct", "LANDFIRE canopy cover", "Fuel-structure context near each segment", CMAP_FUEL, "%", 0, 75, 0.72),
                ("landfire_canopy_height_decoded_m", "LANDFIRE canopy height", "Fuel-structure context near each segment", CMAP_FUEL, "decoded m", 0, 40, 0.72),
            ],
        ),
    ]
    for out in outputs:
        print(out)


if __name__ == "__main__":
    main()
