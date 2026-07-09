import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import contextily as cx
from matplotlib.lines import Line2D


STUDY_CRS = "EPSG:3310"
DISPLAY_CRS = "EPSG:3857"
OUT = PROJECT / "outputs/figures/sci_phase1"

COLORS = {
    "paper": "#fbfaf6",
    "panel": "#f5f3ed",
    "boundary": "#2f3437",
    "context": "#7a7d7f",
    "line": "#2f3a42",
    "line_light": "#4f5961",
    "exo": "#005f73",
    "strict": "#4b7f2c",
    "electrical": "#c27a15",
    "all": "#4d5256",
    "text": "#24292c",
    "grid": "#d9d5cc",
}


def load_data():
    phase1 = PROJECT / "data/processed/phase1"
    study = gpd.read_file(
        phase1 / "study_area_northern_sierra_southern_cascades.gpkg",
        layer="study_area",
    ).to_crs(DISPLAY_CRS)
    segments = gpd.read_file(phase1 / "segments_1km.gpkg", layer="segments_1km").to_crs(DISPLAY_CRS)
    panel = pd.read_csv(phase1 / "segment_year_labels_2017_2023.csv")
    fires = gpd.read_file(PROJECT / "data/raw/calfire/california_historic_fire_perimeters_2017_2023.geojson").to_crs(DISPLAY_CRS)
    bbox_geom = study.geometry.iloc[0]
    fires = fires[fires.intersects(bbox_geom)].copy()
    return study, segments, panel, fires


def setup_ax(ax, study):
    ax.set_facecolor(COLORS["panel"])
    minx, miny, maxx, maxy = study.total_bounds
    pad_x = (maxx - minx) * 0.035
    pad_y = (maxy - miny) * 0.035
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color("#bdb7ad")
    try:
        cx.add_basemap(
            ax,
            crs=DISPLAY_CRS,
            source=cx.providers.CartoDB.Positron,
            zoom=8,
            attribution=False,
            alpha=0.54,
        )
    except Exception as exc:
        print(f"[warn] basemap unavailable: {exc}")


def add_north_arrow(ax, x=0.92, y=0.14):
    ax.annotate(
        "N",
        xy=(x, y + 0.075),
        xytext=(x, y),
        xycoords="axes fraction",
        ha="center",
        va="center",
        fontsize=9,
        color=COLORS["text"],
        arrowprops=dict(arrowstyle="-|>", lw=1.0, color=COLORS["text"]),
    )


def add_scale_bar(ax, length_km=100, location=(0.08, 0.08)):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x = x0 + (x1 - x0) * location[0]
    y = y0 + (y1 - y0) * location[1]
    length_m = length_km * 1000
    ax.plot([x, x + length_m], [y, y], color=COLORS["text"], lw=1.5, solid_capstyle="butt")
    tick = (y1 - y0) * 0.006
    ax.plot([x, x], [y - tick, y + tick], color=COLORS["text"], lw=0.9)
    ax.plot([x + length_m, x + length_m], [y - tick, y + tick], color=COLORS["text"], lw=0.9)
    ax.text(x + length_m / 2, y + (y1 - y0) * 0.014, f"{length_km} km", ha="center", va="bottom", fontsize=7.2, color=COLORS["text"])


def label_segments(segments, panel, field):
    ids = panel.loc[panel[field] == 1, "segment_id"].unique()
    return segments[segments["segment_id"].isin(ids)]


def save_figure(fig, stem):
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{stem}.png"
    pdf = OUT / f"{stem}.pdf"
    fig.savefig(png, dpi=450, bbox_inches="tight", facecolor=COLORS["paper"])
    fig.savefig(pdf, bbox_inches="tight", facecolor=COLORS["paper"])
    print(png)
    print(pdf)


def figure_1(study, segments, panel, fires):
    exo_segments = label_segments(segments, panel, "exogenous_fire_exposure")
    elec_segments = label_segments(segments, panel, "electrical_power_fire_overlap")
    exo_fires = fires[fires["CAUSE"] != 11]
    elec_fires = fires[fires["CAUSE"] == 11]

    fig, ax = plt.subplots(figsize=(6.9, 7.4))
    fig.patch.set_facecolor(COLORS["paper"])
    setup_ax(ax, study)

    exo_fires.boundary.plot(ax=ax, color="#8b8b84", linewidth=0.34, alpha=0.58)
    elec_fires.boundary.plot(ax=ax, color=COLORS["electrical"], linewidth=0.55, alpha=0.88)
    segments.plot(ax=ax, color=COLORS["line_light"], linewidth=0.12, alpha=0.42)
    exo_segments.plot(ax=ax, color=COLORS["exo"], linewidth=0.62, alpha=1.0)
    elec_segments.plot(ax=ax, color=COLORS["electrical"], linewidth=0.58, alpha=0.96)

    ax.set_title(
        "Transmission-line wildfire exposure labels in Northern California",
        fontsize=10.8,
        color=COLORS["text"],
        pad=12,
        loc="left",
    )
    ax.text(
        0.0,
        1.01,
        "1 km CEC line segments, 1 km buffers, CAL FIRE perimeters 2017-2023",
        transform=ax.transAxes,
        fontsize=7.8,
        color="#5f666a",
        ha="left",
    )
    legend = [
        Line2D([0], [0], color=COLORS["exo"], lw=2.4, label="Exogenous-exposure segments"),
        Line2D([0], [0], color=COLORS["electrical"], lw=2.4, label="Electrical-overlap segments"),
        Line2D([0], [0], color=COLORS["line_light"], lw=1.6, label="Other CEC transmission segments"),
        Line2D([0], [0], color="#8b8b84", lw=1.4, label="Non-electrical fire perimeters"),
        Line2D([0], [0], color=COLORS["electrical"], lw=1.4, label="Electrical-power fire perimeters"),
    ]
    ax.legend(
        handles=legend,
        loc="lower left",
        frameon=True,
        framealpha=0.98,
        facecolor="#ffffff",
        edgecolor="#a9a39a",
        fontsize=7.5,
        title="Map layers",
        title_fontsize=8.0,
    )
    add_scale_bar(ax, 100)
    add_north_arrow(ax)
    ax.text(
        0.0,
        -0.045,
        "Sources: CEC transmission lines; CAL FIRE FRAP fire perimeters; CartoDB Positron basemap.",
        transform=ax.transAxes,
        fontsize=6.8,
        color="#6b7073",
        ha="left",
    )
    fig.tight_layout()
    save_figure(fig, "fig1_study_area_transmission_fire_labels")
    plt.close(fig)


def figure_2(study, segments, panel, fires):
    fields = [
        ("all_fire_exposure", "A. All fire exposure", COLORS["all"]),
        ("exogenous_fire_exposure", "B. Exogenous exposure (CAUSE != 11)", COLORS["exo"]),
        ("strict_exogenous_fire_exposure", "C. Strict exogenous (CAUSE not in {11, 2})", COLORS["strict"]),
        ("electrical_power_fire_overlap", "D. Electrical-power overlap diagnostic", COLORS["electrical"]),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11, 10.5))
    fig.patch.set_facecolor(COLORS["paper"])
    for ax, (field, title, color) in zip(axes.ravel(), fields):
        setup_ax(ax, study)
        fires.boundary.plot(ax=ax, color="#777a7c", linewidth=0.20, alpha=0.30)
        segments.plot(ax=ax, color=COLORS["line_light"], linewidth=0.07, alpha=0.22)
        label_segments(segments, panel, field).plot(ax=ax, color=color, linewidth=0.58, alpha=1.0)
        n = int(panel[field].sum())
        ax.set_title(f"{title}\n{n:,} positive segment-year rows", fontsize=10.5, color=COLORS["text"], loc="left")
        add_north_arrow(ax, x=0.92, y=0.11)
    legend = [
        Line2D([0], [0], color=COLORS["all"], lw=2.6, label="All fires"),
        Line2D([0], [0], color=COLORS["exo"], lw=2.6, label="Exogenous"),
        Line2D([0], [0], color=COLORS["strict"], lw=2.6, label="Strict exogenous"),
        Line2D([0], [0], color=COLORS["electrical"], lw=2.6, label="Electrical diagnostic"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=4, frameon=True, framealpha=0.98, facecolor="#ffffff", edgecolor="#a9a39a", fontsize=8.5)
    fig.suptitle("Cause-screened segment-year exposure labels", fontsize=11.8, color=COLORS["text"], x=0.06, ha="left")
    fig.text(0.06, 0.93, "Labels are parallel diagnostic definitions, not mutually exclusive classes.", fontsize=7.8, color="#5f666a")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    save_figure(fig, "fig2_cause_screened_label_maps")
    plt.close(fig)


def figure_3(panel):
    summary = panel.groupby("year")[
        [
            "all_fire_exposure",
            "exogenous_fire_exposure",
            "strict_exogenous_fire_exposure",
            "electrical_power_fire_overlap",
        ]
    ].sum()
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    fig.patch.set_facecolor(COLORS["paper"])
    ax.set_facecolor(COLORS["paper"])
    plot_colors = [COLORS["all"], COLORS["exo"], COLORS["strict"], COLORS["electrical"]]
    summary.plot(kind="bar", ax=ax, color=plot_colors, width=0.78, edgecolor="#ffffff", linewidth=0.3)
    ax.set_title("Annual segment-year exposure labels", fontsize=10.8, color=COLORS["text"], loc="left", pad=9)
    ax.text(
        0,
        1.02,
        "Cause screening materially changes the validation target, especially in 2018 and 2021.",
        transform=ax.transAxes,
        fontsize=7.8,
        color="#5f666a",
        ha="left",
    )
    ax.set_xlabel("")
    ax.set_ylabel("Positive segment-year rows", fontsize=8.4, color=COLORS["text"])
    ax.tick_params(axis="x", rotation=0, labelsize=8, colors=COLORS["text"])
    ax.tick_params(axis="y", labelsize=8, colors=COLORS["text"])
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#cfc9be")
    ax.spines["bottom"].set_color("#cfc9be")
    ax.legend(
        ["All fires", "Exogenous", "Strict exogenous", "Electrical diagnostic"],
        ncol=2,
        frameon=False,
        fontsize=7.6,
        loc="upper right",
    )
    fig.tight_layout()
    save_figure(fig, "fig3_annual_segment_year_label_counts")
    plt.close(fig)


def main():
    study, segments, panel, fires = load_data()
    figure_1(study, segments, panel, fires)
    figure_2(study, segments, panel, fires)
    figure_3(panel)


if __name__ == "__main__":
    main()
