import json
import sys
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import matplotlib.pyplot as plt
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

BAND_LABELS = [
    ("LF2024 FBFM40", "Fuel model code"),
    ("LF2024 canopy cover", "Percent"),
    ("LF2024 canopy height", "Decoded metres (raw / 10)"),
    ("LF2024 canopy base height", "Decoded metres (raw / 10)"),
    ("LF2024 canopy bulk density", "Decoded kg m-3 (raw / 100)"),
]

DECODE_MULTIPLIERS = {
    3: 0.1,
    4: 0.1,
    5: 0.01,
}


def output_zip_from_manifest():
    manifest = DIRS["tables"] / "landfire_lfps_job_manifest.json"
    if not manifest.exists():
        raise FileNotFoundError(manifest)
    with manifest.open(encoding="utf-8") as handle:
        data = json.load(handle)
    out = data.get("output_file")
    if not out:
        raise RuntimeError("LANDFIRE LFPS manifest has no output_file.")
    return Path(out)


def extract_zip(zip_path: Path):
    extract_dir = DIRS["interim_landfire"] / zip_path.stem
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = extract_dir / member
            if not target.exists() or target.stat().st_size == 0:
                zf.extract(member, extract_dir)
    tifs = sorted(extract_dir.glob("*.tif"))
    if not tifs:
        raise FileNotFoundError(f"No tif in {extract_dir}")
    return extract_dir, tifs[0]


def load_reference_lines(crs):
    path = PROJECT / "data/processed/phase1/segments_1km.gpkg"
    if not path.exists():
        return None
    lines = gpd.read_file(path)
    if lines.crs is None:
        lines = lines.set_crs("EPSG:4326")
    return lines.to_crs(crs)


def read_band(src, band_index):
    arr = src.read(band_index, masked=True).astype("float32")
    arr = np.ma.filled(arr, np.nan)
    if band_index in DECODE_MULTIPLIERS:
        arr = arr * DECODE_MULTIPLIERS[band_index]
    return arr


def main():
    ensure_phase2_dirs()
    zip_path = output_zip_from_manifest()
    extract_dir, tif_path = extract_zip(zip_path)

    with rasterio.open(tif_path) as src:
        extent = plotting_extent(src)
        lines = load_reference_lines(src.crs)
        arrays = [read_band(src, i) for i in range(1, min(src.count, 5) + 1)]
        profile = {
            "source_zip": str(zip_path),
            "extract_dir": str(extract_dir),
            "tif": str(tif_path),
            "crs": str(src.crs),
            "bounds": list(src.bounds),
            "width": src.width,
            "height": src.height,
            "count": src.count,
            "band_labels": BAND_LABELS[: len(arrays)],
        }

    fig, axes = plt.subplots(2, 3, figsize=(10.4, 7.1), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    axes_flat = axes.ravel()
    for idx, ax in enumerate(axes_flat):
        if idx >= len(arrays):
            ax.set_axis_off()
            ax.text(
                0.02,
                0.92,
                "LFPS output",
                transform=ax.transAxes,
                fontsize=10,
                fontweight="bold",
                color=COLORS["text"],
                va="top",
            )
            ax.text(
                0.02,
                0.78,
                "Projection: EPSG:5070\nResolution: 90 m\nBands: FBFM40, CC, CH, CBH, CBD\nMetadata XML: included",
                transform=ax.transAxes,
                fontsize=8,
                color=COLORS["axis"],
                va="top",
                linespacing=1.45,
            )
            continue
        arr = arrays[idx]
        title, cbar_label = BAND_LABELS[idx]
        if idx == 0:
            cmap = "YlGnBu"
            vmin, vmax = np.nanpercentile(arr, [1, 99])
        else:
            cmap = "cividis"
            vmin, vmax = np.nanpercentile(arr, [2, 98])
        im = ax.imshow(arr, extent=extent, cmap=cmap, vmin=vmin, vmax=vmax)
        if lines is not None:
            lines.plot(ax=ax, color=COLORS["line"], linewidth=0.1, alpha=0.22, zorder=4)
        cb = fig.colorbar(im, ax=ax, shrink=0.76, pad=0.015)
        cb.set_label(cbar_label, fontsize=6.8, color=COLORS["axis"])
        cb.ax.tick_params(labelsize=6, colors=COLORS["axis"], length=2)
        cb.outline.set_linewidth(0.4)
        ax.set_title(title, fontsize=8.8, color=COLORS["text"], pad=8)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#44494d")
            spine.set_linewidth(0.55)

    fig.suptitle("LANDFIRE LF2024 fuel and canopy covariate layers", fontsize=11, color=COLORS["text"], y=0.982)
    fig.text(
        0.5,
        0.018,
        "LFPS multi-band GeoTIFF clipped to the Northern Sierra / Southern Cascades domain. Thin dark overlays show 1 km CEC transmission-line segments.",
        ha="center",
        va="bottom",
        fontsize=7.1,
        color=COLORS["axis"],
    )
    fig.subplots_adjust(left=0.035, right=0.965, top=0.91, bottom=0.095, wspace=0.25, hspace=0.24)
    out = DIRS["preview"] / "phase2_landfire_preview.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)

    profile_out = DIRS["tables"] / "landfire_lfps_output_manifest.json"
    profile_out.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(out)
    print(profile_out)


if __name__ == "__main__":
    main()
