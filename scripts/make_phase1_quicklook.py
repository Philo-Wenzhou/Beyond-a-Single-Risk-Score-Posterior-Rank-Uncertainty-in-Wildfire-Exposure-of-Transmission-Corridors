import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd


STUDY_CRS = "EPSG:3310"


def main():
    phase1 = PROJECT / "data/processed/phase1"
    out_dir = PROJECT / "outputs/figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    segments = gpd.read_file(phase1 / "segments_1km.gpkg", layer="segments_1km").to_crs(STUDY_CRS)
    study = gpd.read_file(phase1 / "study_area_northern_sierra_southern_cascades.gpkg", layer="study_area").to_crs(STUDY_CRS)
    fires = gpd.read_file(PROJECT / "data/raw/calfire/california_historic_fire_perimeters_2017_2023.geojson").to_crs(STUDY_CRS)
    panel = pd.read_csv(phase1 / "segment_year_labels_2017_2023.csv")

    bbox = study.geometry.iloc[0]
    fires = fires[fires.intersects(bbox)].copy()
    exo_segments = panel.loc[panel["exogenous_fire_exposure"] == 1, "segment_id"].unique()
    elec_segments = panel.loc[panel["electrical_power_fire_overlap"] == 1, "segment_id"].unique()

    exo_gdf = segments[segments["segment_id"].isin(exo_segments)]
    elec_gdf = segments[segments["segment_id"].isin(elec_segments)]
    elec_fires = fires[fires["CAUSE"] == 11]
    exo_fires = fires[fires["CAUSE"] != 11]

    fig, axes = plt.subplots(1, 2, figsize=(14, 8), dpi=220)
    for ax in axes:
        study.boundary.plot(ax=ax, color="black", linewidth=1.0)
        ax.set_axis_off()
        ax.set_aspect("equal")

    exo_fires.boundary.plot(ax=axes[0], color="#d95f02", linewidth=0.45, alpha=0.8)
    segments.plot(ax=axes[0], color="#4d4d4d", linewidth=0.08, alpha=0.35)
    exo_gdf.plot(ax=axes[0], color="#1b9e77", linewidth=0.45, alpha=0.95)
    axes[0].set_title("External wildfire exposure labels\\nCAUSE != 11, 2017-2023", fontsize=11)

    elec_fires.boundary.plot(ax=axes[1], color="#7570b3", linewidth=0.6, alpha=0.9)
    segments.plot(ax=axes[1], color="#4d4d4d", linewidth=0.08, alpha=0.35)
    elec_gdf.plot(ax=axes[1], color="#e7298a", linewidth=0.5, alpha=0.95)
    axes[1].set_title("Electrical-power-fire overlap diagnostic\\nCAUSE = 11, 2017-2023", fontsize=11)

    fig.suptitle("Phase 1 quicklook: 1 km transmission-line segments and CAL FIRE labels", fontsize=13)
    fig.tight_layout()
    png = out_dir / "phase1_quicklook_segments_fire_labels.png"
    fig.savefig(png, bbox_inches="tight")
    plt.close(fig)

    summary = panel.groupby("year")[
        [
            "all_fire_exposure",
            "exogenous_fire_exposure",
            "strict_exogenous_fire_exposure",
            "electrical_power_fire_overlap",
        ]
    ].sum()
    fig, ax = plt.subplots(figsize=(9, 5), dpi=220)
    summary.plot(kind="bar", ax=ax, color=["#666666", "#1b9e77", "#66a61e", "#e7298a"])
    ax.set_xlabel("Year")
    ax.set_ylabel("Positive segment-year rows")
    ax.set_title("Phase 1 annual label counts")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    bar_png = out_dir / "phase1_annual_label_counts.png"
    fig.savefig(bar_png, bbox_inches="tight")
    plt.close(fig)

    print(png)
    print(bar_png)


if __name__ == "__main__":
    main()

