import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import requests

from phase2_data_config import DIRS, STUDY_BBOX_WGS84, ensure_phase2_dirs


USGS_3DEP_EXPORT = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"


def main():
    ensure_phase2_dirs()
    out = DIRS["raw_dem"] / "usgs_3dep_dem_study_area_2048.tif"
    if out.exists() and out.stat().st_size > 1024:
        print(f"[skip] {out}")
    else:
        bbox = ",".join(str(v) for v in STUDY_BBOX_WGS84)
        params = {
            "f": "image",
            "bbox": bbox,
            "bboxSR": "4326",
            "imageSR": "4326",
            "size": "2048,1560",
            "format": "tiff",
            "pixelType": "F32",
            "noData": "-999999",
            "interpolation": "RSP_BilinearInterpolation",
        }
        print(f"[download] USGS 3DEP DEM -> {out}")
        r = requests.get(USGS_3DEP_EXPORT, params=params, timeout=180)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        if "image" not in content_type and "tiff" not in content_type and len(r.content) < 1024 * 1024:
            raise RuntimeError(f"Unexpected DEM response: {content_type} {r.text[:500]}")
        out.write_bytes(r.content)
        print(f"[data] {out} {out.stat().st_size}")
    manifest = {
        "source": USGS_3DEP_EXPORT,
        "bbox_wgs84": STUDY_BBOX_WGS84,
        "target": str(out),
        "role": "terrain preview and slope/ruggedness covariate source",
    }
    (DIRS["tables"] / "dem_download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
