import json
import math
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString, box
from shapely.ops import substring


STUDY_BBOX_WGS84 = (-123.2, 38.6, -119.0, 41.8)
STUDY_CRS = "EPSG:3310"
SEGMENT_LENGTH_M = 1000
BUFFER_RADIUS_M = 1000
YEARS = list(range(2017, 2024))


def read_layer(path: Path, bbox=None) -> gpd.GeoDataFrame:
    return gpd.read_file(path, bbox=bbox)


def iter_lines(geom):
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, LineString):
        yield geom
    elif isinstance(geom, MultiLineString):
        for part in geom.geoms:
            if not part.is_empty:
                yield part


def split_line(line: LineString, segment_length: float):
    length = line.length
    if length == 0:
        return
    n = max(1, math.ceil(length / segment_length))
    for idx in range(n):
        start = idx * segment_length
        end = min((idx + 1) * segment_length, length)
        if end <= start:
            continue
        part = substring(line, start, end)
        if not part.is_empty and part.length > 0:
            yield idx, part


def safe_text(value):
    if pd.isna(value):
        return None
    return str(value)


def build_segments(lines: gpd.GeoDataFrame, study_area_3310) -> gpd.GeoDataFrame:
    rows = []
    segment_counter = 0
    for _, row in lines.iterrows():
        attrs = row.drop(labels="geometry").to_dict()
        line_objectid = attrs.get("OBJECTID")
        for line in iter_lines(row.geometry):
            clipped = line.intersection(study_area_3310)
            for clipped_line in iter_lines(clipped):
                for part_idx, part in split_line(clipped_line, SEGMENT_LENGTH_M):
                    segment_counter += 1
                    rows.append(
                        {
                            "segment_id": f"seg_{segment_counter:06d}",
                            "source_objectid": line_objectid,
                            "part_index": part_idx,
                            "length_m": float(part.length),
                            "line_name": safe_text(attrs.get("Name")),
                            "tline_name": safe_text(attrs.get("TLine_Name")),
                            "kv": safe_text(attrs.get("kV")),
                            "kv_sort": attrs.get("kV_Sort"),
                            "owner": safe_text(attrs.get("Owner")),
                            "status": safe_text(attrs.get("Status")),
                            "circuit": safe_text(attrs.get("Circuit")),
                            "line_type": safe_text(attrs.get("Type")),
                            "geometry": part,
                        }
                    )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=STUDY_CRS)


def add_fire_labels(segments: gpd.GeoDataFrame, fires: gpd.GeoDataFrame) -> pd.DataFrame:
    buffers = segments[["segment_id", "geometry"]].copy()
    buffers["geometry"] = buffers.geometry.buffer(BUFFER_RADIUS_M)
    buffers = buffers.set_geometry("geometry")
    sindex = buffers.sindex

    labels = {
        year: {
            "all_fire_exposure": set(),
            "exogenous_fire_exposure": set(),
            "strict_exogenous_fire_exposure": set(),
            "electrical_power_fire_overlap": set(),
        }
        for year in YEARS
    }
    fire_counts = {year: {} for year in YEARS}
    largest_fire = {year: {} for year in YEARS}

    for _, fire in fires.iterrows():
        year = fire.get("YEAR_")
        if pd.isna(year):
            continue
        year = int(year)
        if year not in labels:
            continue
        geom = fire.geometry
        if geom is None or geom.is_empty:
            continue
        idxs = sindex.query(geom, predicate="intersects")
        if len(idxs) == 0:
            continue
        cause = fire.get("CAUSE")
        cause = None if pd.isna(cause) else int(cause)
        fire_name = safe_text(fire.get("FIRE_NAME"))
        acres = float(fire.get("GIS_ACRES") or 0)
        for idx in idxs:
            segment_id = buffers.iloc[idx]["segment_id"]
            labels[year]["all_fire_exposure"].add(segment_id)
            if cause != 11:
                labels[year]["exogenous_fire_exposure"].add(segment_id)
            if cause not in (11, 2):
                labels[year]["strict_exogenous_fire_exposure"].add(segment_id)
            if cause == 11:
                labels[year]["electrical_power_fire_overlap"].add(segment_id)

            fire_counts[year][segment_id] = fire_counts[year].get(segment_id, 0) + 1
            current = largest_fire[year].get(segment_id)
            if current is None or acres > current["largest_fire_acres"]:
                largest_fire[year][segment_id] = {
                    "largest_fire_name": fire_name,
                    "largest_fire_acres": acres,
                    "dominant_cause": cause,
                }

    panel_rows = []
    segment_attrs = segments.drop(columns="geometry").copy()
    for _, seg in segment_attrs.iterrows():
        segment_id = seg["segment_id"]
        base = seg.to_dict()
        for year in YEARS:
            row = dict(base)
            row["year"] = year
            for field in labels[year]:
                row[field] = int(segment_id in labels[year][field])
            row["intersect_fire_count"] = fire_counts[year].get(segment_id, 0)
            lf = largest_fire[year].get(segment_id, {})
            row["largest_fire_name"] = lf.get("largest_fire_name")
            row["largest_fire_acres"] = lf.get("largest_fire_acres", 0.0)
            row["dominant_cause"] = lf.get("dominant_cause")
            panel_rows.append(row)

    return pd.DataFrame(panel_rows)


def main():
    raw_cec = PROJECT / "data/raw/cec/california_electric_transmission_lines.geojson"
    raw_fire = PROJECT / "data/raw/calfire/california_historic_fire_perimeters_2017_2023.geojson"
    out_dir = PROJECT / "data/processed/phase1"
    out_dir.mkdir(parents=True, exist_ok=True)

    bbox_wgs84 = box(*STUDY_BBOX_WGS84)
    bbox_gdf = gpd.GeoDataFrame([{"name": "northern_sierra_southern_cascades", "geometry": bbox_wgs84}], crs="EPSG:4326")
    study_area = bbox_gdf.to_crs(STUDY_CRS).geometry.iloc[0]

    print("Reading CEC transmission lines...")
    lines = read_layer(raw_cec, bbox=STUDY_BBOX_WGS84)
    lines = lines.to_crs(STUDY_CRS)
    lines = lines[lines.geometry.notna() & ~lines.geometry.is_empty].copy()
    print(f"CEC lines in bbox: {len(lines)}")

    print("Splitting lines into 1 km segments...")
    segments = build_segments(lines, study_area)
    segments = segments[segments.geometry.notna() & ~segments.geometry.is_empty].copy()
    print(f"Segments: {len(segments)}")

    print("Reading CAL FIRE perimeters...")
    # Slightly expanded bbox catches fire polygons that intersect 1 km buffers near the boundary.
    minx, miny, maxx, maxy = STUDY_BBOX_WGS84
    fire_bbox = (minx - 0.05, miny - 0.05, maxx + 0.05, maxy + 0.05)
    fires = read_layer(raw_fire, bbox=fire_bbox)
    fires = fires[fires["YEAR_"].isin(YEARS)].copy()
    fires = fires.to_crs(STUDY_CRS)
    fires = fires[fires.geometry.notna() & ~fires.geometry.is_empty].copy()
    print(f"Fire perimeters in bbox: {len(fires)}")

    print("Building segment-year labels...")
    panel = add_fire_labels(segments, fires)
    print(f"Segment-year rows: {len(panel)}")

    segments_wgs84 = segments.to_crs("EPSG:4326")
    buffers = segments.copy()
    buffers["geometry"] = buffers.geometry.buffer(BUFFER_RADIUS_M)
    buffers_wgs84 = buffers.to_crs("EPSG:4326")
    bbox_gdf.to_file(out_dir / "study_area_northern_sierra_southern_cascades.gpkg", layer="study_area", driver="GPKG")
    segments_wgs84.to_file(out_dir / "segments_1km.gpkg", layer="segments_1km", driver="GPKG")
    buffers_wgs84.to_file(out_dir / "segment_buffers_1km.gpkg", layer="segment_buffers_1km", driver="GPKG")
    panel.to_csv(out_dir / "segment_year_labels_2017_2023.csv", index=False, encoding="utf-8")

    summary = {
        "study_bbox_wgs84": STUDY_BBOX_WGS84,
        "study_crs": STUDY_CRS,
        "segment_length_m": SEGMENT_LENGTH_M,
        "buffer_radius_m": BUFFER_RADIUS_M,
        "years": YEARS,
        "cec_lines_in_bbox": int(len(lines)),
        "segments": int(len(segments)),
        "fire_perimeters_in_bbox": int(len(fires)),
        "segment_year_rows": int(len(panel)),
        "label_sums": {
            field: int(panel[field].sum())
            for field in [
                "all_fire_exposure",
                "exogenous_fire_exposure",
                "strict_exogenous_fire_exposure",
                "electrical_power_fire_overlap",
            ]
        },
    }
    (out_dir / "phase1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

