import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


CAUSE_NAMES = {
    1: "Lightning",
    2: "Equipment Use",
    3: "Smoking",
    4: "Campfire",
    5: "Debris",
    6: "Railroad",
    7: "Arson",
    8: "Playing with Fire",
    9: "Miscellaneous",
    10: "Vehicle",
    11: "Electrical Power",
    12: "Firefighter Training",
    13: "Non-Firefighter Training",
    14: "Unknown / Unidentified",
    15: "Structure",
    16: "Aircraft",
    17: "Volcanic",
    18: "Escaped Prescribed Burn",
    19: "Illegal Alien Campfire",
    None: "Null",
}


def main():
    project = Path(__file__).resolve().parents[1]
    source = project / "data/raw/calfire/california_historic_fire_perimeters_2017_2023.geojson"
    out_dir = project / "outputs/tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    with source.open("r", encoding="utf-8-sig") as f:
        features = json.load(f)["features"]

    counts = Counter()
    acres = defaultdict(float)
    by_year = defaultdict(Counter)
    electrical_rows = []

    for feature in features:
        props = feature.get("properties") or {}
        cause = props.get("CAUSE")
        year = props.get("YEAR_")
        gis_acres = float(props.get("GIS_ACRES") or 0)
        counts[cause] += 1
        acres[cause] += gis_acres
        by_year[cause][year] += 1
        if cause == 11:
            electrical_rows.append(
                {
                    "YEAR_": year,
                    "FIRE_NAME": props.get("FIRE_NAME"),
                    "GIS_ACRES": gis_acres,
                    "UNIT_ID": props.get("UNIT_ID"),
                    "AGENCY": props.get("AGENCY"),
                }
            )

    with (out_dir / "calfire_cause_summary_2017_2023.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cause_code", "cause_name", "fire_count", "gis_acres"])
        for cause, count in counts.most_common():
            writer.writerow([cause, CAUSE_NAMES.get(cause, "Unknown code"), count, round(acres[cause], 2)])

    with (out_dir / "calfire_electrical_power_fires_2017_2023.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["YEAR_", "FIRE_NAME", "GIS_ACRES", "UNIT_ID", "AGENCY"])
        writer.writeheader()
        for row in sorted(electrical_rows, key=lambda r: r["GIS_ACRES"], reverse=True):
            writer.writerow(row)

    print(f"features={len(features)}")
    print(f"electrical_power_count={counts[11]}")
    print(f"electrical_power_acres={acres[11]:.2f}")


if __name__ == "__main__":
    main()

