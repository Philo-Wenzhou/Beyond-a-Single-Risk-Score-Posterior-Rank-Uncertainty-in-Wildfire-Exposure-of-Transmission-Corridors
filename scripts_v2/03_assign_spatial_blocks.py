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
import numpy as np
import pandas as pd

from utils_v2 import PROJECT, load_config, require_audit_first, write_json, write_text


OUT_DIR = PROJECT / "data_intermediate/v2/spatial_blocks"
AUDIT_DIR = PROJECT / "outputs/v2/audit"


def assign_block(values, origin, size_m):
    idx = np.floor((values - origin) / size_m).astype("int64")
    return idx


def main():
    require_audit_first()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    project_crs = config["spatial"]["project_crs"]

    segments = gpd.read_file(PROJECT / config["paths"]["segments_1km"])
    if segments.crs is None:
        segments = segments.set_crs("EPSG:4326")
    seg = segments[["segment_id", "geometry"]].to_crs(project_crs).copy()
    cent = seg.geometry.centroid
    xmin, ymin, xmax, ymax = seg.total_bounds

    out = pd.DataFrame(
        {
            "segment_id": seg["segment_id"].values,
            "centroid_x_m": cent.x.values,
            "centroid_y_m": cent.y.values,
        }
    )

    summary = {
        "project_crs": project_crs,
        "segment_count": int(len(out)),
        "anchor_xmin_m": float(xmin),
        "anchor_ymin_m": float(ymin),
        "bounds_m": [float(xmin), float(ymin), float(xmax), float(ymax)],
        "block_sizes_m": config["spatial"]["block_sizes_m"],
    }

    for size in config["spatial"]["block_sizes_m"]:
        ix = assign_block(out["centroid_x_m"].to_numpy(), xmin, size)
        iy = assign_block(out["centroid_y_m"].to_numpy(), ymin, size)
        label = f"{int(size/1000)}km"
        out[f"block_{label}_ix"] = ix
        out[f"block_{label}_iy"] = iy
        out[f"block_{label}_id"] = [f"b{int(size/1000):02d}_{x:03d}_{y:03d}" for x, y in zip(ix, iy)]
        counts = out[f"block_{label}_id"].value_counts()
        summary[f"block_{label}_count"] = int(counts.size)
        summary[f"block_{label}_segment_count_quantiles"] = counts.quantile([0, 0.1, 0.5, 0.9, 1.0]).to_dict()

    out.to_parquet(OUT_DIR / "segment_spatial_blocks.parquet", index=False)
    out.to_csv(OUT_DIR / "segment_spatial_blocks.csv", index=False)
    write_json(AUDIT_DIR / "SPATIAL_BLOCKS_QA.json", summary)

    md = "# Spatial Blocks QA\n\n"
    md += f"- Project CRS: `{project_crs}`\n"
    md += f"- Segment count: {summary['segment_count']}\n"
    md += f"- Anchor lower-left: ({summary['anchor_xmin_m']:.3f}, {summary['anchor_ymin_m']:.3f}) m\n"
    for size in config["spatial"]["block_sizes_m"]:
        label = f"{int(size/1000)}km"
        md += f"- {label} blocks: {summary[f'block_{label}_count']}, segment-count quantiles: `{summary[f'block_{label}_segment_count_quantiles']}`\n"
    write_text(AUDIT_DIR / "SPATIAL_BLOCKS_QA.md", md)
    print(f"[done] {OUT_DIR / 'segment_spatial_blocks.parquet'}")


if __name__ == "__main__":
    main()
