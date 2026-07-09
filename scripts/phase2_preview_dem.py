import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.plot import plotting_extent

from phase2_data_config import DIRS, ensure_phase2_dirs


COLORS = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "line": "#25292c",
}


def load_reference_lines():
    path = PROJECT / "data/processed/phase1/segments_1km.gpkg"
    if not path.exists():
        return None
    lines = gpd.read_file(path)
    if lines.crs is None:
        lines = lines.set_crs("EPSG:4326")
    return lines.to_crs("EPSG:4326")


def main():
    ensure_phase2_dirs()
    dem = DIRS["raw_dem"] / "usgs_3dep_dem_study_area_2048.tif"
    if not dem.exists():
        raise FileNotFoundError(dem)
    with rasterio.open(dem) as src:
        arr = src.read(1).astype("float32")
        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan
        extent = plotting_extent(src)
    gy, gx = np.gradient(arr)
    slope = np.sqrt(gx * gx + gy * gy)
    lines = load_reference_lines()
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.8), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    im0 = axes[0].imshow(arr, extent=extent, cmap="gist_earth", vmin=np.nanpercentile(arr, 1), vmax=np.nanpercentile(arr, 99))
    axes[0].set_title("USGS 3DEP elevation", fontsize=10, color=COLORS["text"])
    im1 = axes[1].imshow(slope, extent=extent, cmap="cividis", vmax=np.nanpercentile(slope, 98))
    axes[1].set_title("Relative terrain gradient", fontsize=10, color=COLORS["text"])
    for ax in axes:
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.tick_params(labelsize=7, colors=COLORS["axis"], length=2.5, width=0.5)
        for spine in ax.spines.values():
            spine.set_color("#44494d")
            spine.set_linewidth(0.6)
        if lines is not None:
            lines.plot(ax=ax, color=COLORS["line"], linewidth=0.12, alpha=0.28, zorder=4)
    cb0 = fig.colorbar(im0, ax=axes[0], shrink=0.78, label="Elevation")
    cb1 = fig.colorbar(im1, ax=axes[1], shrink=0.78, label="Gradient")
    for cb in (cb0, cb1):
        cb.ax.tick_params(labelsize=6.2, colors=COLORS["axis"], length=2)
        cb.outline.set_linewidth(0.4)
    fig.suptitle("Terrain covariate preview for transmission-line exposure modeling", fontsize=11, color=COLORS["text"])
    fig.text(
        0.5,
        0.018,
        "Thin dark overlays show 1 km CEC transmission-line segments. Gradient is a relative preview field; final slope/aspect covariates should be computed in a metric CRS.",
        ha="center",
        va="bottom",
        fontsize=7.1,
        color=COLORS["axis"],
    )
    fig.tight_layout(rect=(0.01, 0.05, 0.995, 0.94), w_pad=1.2)
    out = DIRS["preview"] / "phase2_dem_preview.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
