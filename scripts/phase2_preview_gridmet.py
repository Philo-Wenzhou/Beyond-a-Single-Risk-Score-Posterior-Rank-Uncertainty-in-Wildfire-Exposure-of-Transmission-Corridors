import sys
import shutil
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import matplotlib.pyplot as plt
import xarray as xr

from phase2_data_config import DIRS, GRIDMET_VARIABLES, STUDY_BBOX_WGS84, ensure_phase2_dirs


COLORS = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "line": "#25292c",
}

VAR_LABELS = {
    "fm100": "100-h fuel moisture",
    "fm1000": "1000-h fuel moisture",
    "vpd": "Vapor pressure deficit",
    "erc": "Energy release component",
    "bi": "Burning index",
    "vs": "Wind speed",
    "rmin": "Minimum relative humidity",
    "pr": "Precipitation",
}


def pick_var(ds):
    for name in ds.data_vars:
        if name not in {"crs", "day"}:
            return name
    return list(ds.data_vars)[0]


def load_dataset_ascii(path: Path):
    with tempfile.TemporaryDirectory(prefix="gridmet_preview_ascii_") as tmpdir:
        tmp_path = Path(tmpdir) / path.name
        shutil.copy2(path, tmp_path)
        with xr.open_dataset(tmp_path) as ds:
            return ds.load()


def load_reference_lines():
    path = PROJECT / "data/processed/phase1/segments_1km.gpkg"
    if not path.exists():
        return None
    lines = gpd.read_file(path)
    if lines.crs is None:
        lines = lines.set_crs("EPSG:4326")
    return lines.to_crs("EPSG:4326")


def plot_var(ax, var, year, lines=None):
    path = DIRS["interim_gridmet"] / f"{var}_{year}_study_area.nc"
    if not path.exists():
        ax.set_axis_off()
        ax.set_title(f"{var} {year}\nmissing", fontsize=8)
        return
    ds = load_dataset_ascii(path)
    data_var = pick_var(ds)
    da = ds[data_var]
    if "day" in da.dims:
        if var in {"fm100", "fm1000", "rmin"}:
            img = da.quantile(0.05, dim="day", skipna=True)
            stat = "p05"
        elif var == "pr":
            img = da.sum(dim="day", skipna=True)
            stat = "sum"
        else:
            img = da.quantile(0.95, dim="day", skipna=True)
            stat = "p95"
    elif "time" in da.dims:
        img = da.quantile(0.95, dim="time", skipna=True)
        stat = "p95"
    else:
        img = da
        stat = "value"
    mappable = img.plot(ax=ax, cmap="cividis", add_colorbar=False, robust=True)
    if lines is not None:
        lines.plot(ax=ax, color=COLORS["line"], linewidth=0.12, alpha=0.24, zorder=4)
    cbar = plt.colorbar(mappable, ax=ax, fraction=0.036, pad=0.018)
    cbar.ax.tick_params(labelsize=5.8, length=2, colors=COLORS["axis"])
    cbar.outline.set_linewidth(0.4)
    ax.set_title(f"{VAR_LABELS.get(var, var)}\n{year} {stat}", fontsize=8.2, color=COLORS["text"])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xlim(STUDY_BBOX_WGS84[0], STUDY_BBOX_WGS84[2])
    ax.set_ylim(STUDY_BBOX_WGS84[1], STUDY_BBOX_WGS84[3])
    ax.tick_params(labelsize=5.8, colors=COLORS["axis"], length=2.5, width=0.5)
    for spine in ax.spines.values():
        spine.set_color("#44494d")
        spine.set_linewidth(0.55)
    ds.close()


def main():
    ensure_phase2_dirs()
    year = 2021
    vars_to_plot = ["fm100", "vpd", "erc", "vs", "rmin", "pr"]
    lines = load_reference_lines()
    fig, axes = plt.subplots(2, 3, figsize=(9.4, 6.0), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    for ax, var in zip(axes.ravel(), vars_to_plot):
        plot_var(ax, var, year, lines=lines)
    fig.suptitle(
        "gridMET study-area preview, 2021 annual extreme/aggregate fields",
        fontsize=11,
        color=COLORS["text"],
        y=0.988,
    )
    fig.text(
        0.5,
        0.018,
        "Thin dark overlays show 1 km CEC transmission-line segments clipped to the Northern Sierra / Southern Cascades study domain.",
        ha="center",
        va="bottom",
        fontsize=7.2,
        color=COLORS["axis"],
    )
    fig.tight_layout(rect=(0.012, 0.04, 0.995, 0.955), w_pad=1.0, h_pad=1.2)
    out = DIRS["preview"] / "phase2_gridmet_preview_2021.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
