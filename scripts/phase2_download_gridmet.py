import json
import sys
import shutil
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import requests
import xarray as xr

from phase2_data_config import DIRS, GRIDMET_VARIABLES, STUDY_BBOX_WGS84, YEARS, ensure_phase2_dirs


BASE_URL = "https://www.northwestknowledge.net/metdata/data"


def download_file(url: str, target: Path, timeout=60):
    if target.exists() and target.stat().st_size > 1024:
        print(f"[skip] {target.name}")
        return
    tmp = target.with_suffix(target.suffix + ".part")
    print(f"[download] {url}")
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    tmp.replace(target)


def subset_gridmet(raw_path: Path, out_path: Path, var: str):
    if out_path.exists() and out_path.stat().st_size > 1024:
        print(f"[skip subset] {out_path.name}")
        return
    minx, miny, maxx, maxy = STUDY_BBOX_WGS84
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gridmet_ascii_") as tmpdir:
        tmpdir = Path(tmpdir)
        raw_tmp = tmpdir / raw_path.name
        out_tmp = tmpdir / out_path.name
        shutil.copy2(raw_path, raw_tmp)
        ds = xr.open_dataset(raw_tmp)
        lon_name = "lon" if "lon" in ds.coords else "longitude"
        lat_name = "lat" if "lat" in ds.coords else "latitude"
        lon = ds[lon_name]
        if float(lon.max()) > 180:
            minx_ = minx % 360
            maxx_ = maxx % 360
        else:
            minx_, maxx_ = minx, maxx
        lat_vals = ds[lat_name].values
        if lat_vals[0] < lat_vals[-1]:
            sub = ds.sel({lon_name: slice(minx_, maxx_), lat_name: slice(miny, maxy)})
        else:
            sub = ds.sel({lon_name: slice(minx_, maxx_), lat_name: slice(maxy, miny)})
        sub.to_netcdf(out_tmp)
        sub.close()
        ds.close()
        shutil.move(str(out_tmp), str(out_path))
    print(f"[subset] {out_path}")


def main():
    ensure_phase2_dirs()
    manifest = []
    for var in GRIDMET_VARIABLES:
        for year in YEARS:
            raw = DIRS["raw_gridmet"] / f"{var}_{year}.nc"
            url = f"{BASE_URL}/{var}_{year}.nc"
            try:
                download_file(url, raw)
                subset = DIRS["interim_gridmet"] / f"{var}_{year}_study_area.nc"
                subset_gridmet(raw, subset, var)
                manifest.append({"variable": var, "year": year, "raw": str(raw), "subset": str(subset), "status": "ok"})
            except Exception as exc:
                print(f"[error] {var} {year}: {exc}", file=sys.stderr)
                manifest.append({"variable": var, "year": year, "raw": str(raw), "status": "error", "error": str(exc)})
    out = DIRS["tables"] / "gridmet_download_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[manifest] {out}")


if __name__ == "__main__":
    main()
