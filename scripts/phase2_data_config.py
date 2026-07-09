from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]

ENV1_PYTHON = Path(r"C:\Users\philo\.conda\envs\env1\python.exe")

STUDY_BBOX_WGS84 = (-123.2, 38.6, -119.0, 41.8)
YEARS = list(range(2017, 2024))

GRIDMET_VARIABLES = {
    "fm100": "100-hour dead fuel moisture",
    "fm1000": "1000-hour dead fuel moisture",
    "vpd": "vapor pressure deficit",
    "erc": "energy release component",
    "bi": "burning index",
    "vs": "wind speed",
    "rmin": "minimum relative humidity",
    "pr": "precipitation",
}

DIRS = {
    "raw_gridmet": PROJECT / "data/raw/gridmet",
    "interim_gridmet": PROJECT / "data/interim/gridmet_study_area",
    "raw_dem": PROJECT / "data/raw/dem_3dep",
    "interim_dem": PROJECT / "data/interim/dem_study_area",
    "raw_landfire": PROJECT / "data/raw/landfire",
    "interim_landfire": PROJECT / "data/interim/landfire_study_area",
    "preview": PROJECT / "outputs/figures/data_previews",
    "tables": PROJECT / "outputs/tables",
    "logs": PROJECT / "logs",
}


def ensure_phase2_dirs():
    for path in DIRS.values():
        path.mkdir(parents=True, exist_ok=True)

