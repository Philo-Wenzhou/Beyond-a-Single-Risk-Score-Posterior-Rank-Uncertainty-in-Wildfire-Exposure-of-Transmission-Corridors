import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

from phase2_data_config import DIRS, GRIDMET_VARIABLES, YEARS, ensure_phase2_dirs


LANDFIRE_REQUIRED_LAYERS = [
    "LF2024_FBFM40",
    "LF2024_CC",
    "LF2024_CH",
    "LF2024_CBH",
    "LF2024_CBD",
]


def main():
    ensure_phase2_dirs()
    rows = []
    for var in GRIDMET_VARIABLES:
        for year in YEARS:
            raw = DIRS["raw_gridmet"] / f"{var}_{year}.nc"
            subset = DIRS["interim_gridmet"] / f"{var}_{year}_study_area.nc"
            rows.append(
                {
                    "dataset": "gridMET",
                    "variable": var,
                    "year": year,
                    "raw_exists": raw.exists(),
                    "raw_mb": round(raw.stat().st_size / 1024 / 1024, 2) if raw.exists() else 0,
                    "subset_exists": subset.exists(),
                    "subset_mb": round(subset.stat().st_size / 1024 / 1024, 2) if subset.exists() else 0,
                }
            )
    dem = DIRS["raw_dem"] / "usgs_3dep_dem_study_area_2048.tif"
    products_path = DIRS["raw_landfire"] / "lfps_products.json"
    products = []
    if products_path.exists():
        with products_path.open(encoding="utf-8") as handle:
            products = json.load(handle).get("products", [])
    product_layer_names = {row.get("layerName") for row in products}
    landfire_job_manifest = DIRS["tables"] / "landfire_lfps_job_manifest.json"
    landfire_output = None
    landfire_job_id = None
    landfire_tif = None
    if landfire_job_manifest.exists():
        with landfire_job_manifest.open(encoding="utf-8") as handle:
            job = json.load(handle)
        landfire_output = job.get("output_file")
        landfire_job_id = job.get("job_id")
    landfire_output_manifest = DIRS["tables"] / "landfire_lfps_output_manifest.json"
    if landfire_output_manifest.exists():
        with landfire_output_manifest.open(encoding="utf-8") as handle:
            landfire_tif = json.load(handle).get("tif")

    status = {
        "gridmet_total_expected": len(GRIDMET_VARIABLES) * len(YEARS),
        "gridmet_raw_done": sum(1 for r in rows if r["raw_exists"]),
        "gridmet_subset_done": sum(1 for r in rows if r["subset_exists"]),
        "dem_exists": dem.exists(),
        "dem_mb": round(dem.stat().st_size / 1024 / 1024, 2) if dem.exists() else 0,
        "landfire_products_catalog_exists": products_path.exists(),
        "landfire_products_count": len(products),
        "landfire_required_layers_available": {
            layer: layer in product_layer_names for layer in LANDFIRE_REQUIRED_LAYERS
        },
        "landfire_job_id": landfire_job_id,
        "landfire_output_exists": bool(landfire_output and Path(landfire_output).exists()),
        "landfire_output_mb": round(Path(landfire_output).stat().st_size / 1024 / 1024, 2)
        if landfire_output and Path(landfire_output).exists()
        else 0,
        "landfire_tif_exists": bool(landfire_tif and Path(landfire_tif).exists()),
        "landfire_tif_mb": round(Path(landfire_tif).stat().st_size / 1024 / 1024, 2)
        if landfire_tif and Path(landfire_tif).exists()
        else 0,
        "gridmet_rows": rows,
    }
    out = DIRS["tables"] / "phase2_data_status.json"
    out.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in status.items() if k != "gridmet_rows"}, indent=2))
    print(f"[status] {out}")


if __name__ == "__main__":
    main()
