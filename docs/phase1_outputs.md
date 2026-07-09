# Phase 1 Outputs

Phase 1 created the public receptor geometry and annual fire-exposure labels for
the approved Northern Sierra / Southern Cascades study area.

## Study Area

```text
lon: -123.2 to -119.0
lat:  38.6 to   41.8
```

## Main Settings

| Setting | Value |
|---|---:|
| Transmission-line source | CEC California Electric Transmission Lines |
| Segment length | 1 km |
| Buffer radius | 1 km |
| Years | 2017-2023 |
| Projected CRS for processing | EPSG:3310 |

## Output Files

| Output | Path |
|---|---|
| Study area polygon | `data/processed/phase1/study_area_northern_sierra_southern_cascades.gpkg` |
| 1 km line segments | `data/processed/phase1/segments_1km.gpkg` |
| 1 km segment buffers | `data/processed/phase1/segment_buffers_1km.gpkg` |
| Segment-year label table | `data/processed/phase1/segment_year_labels_2017_2023.csv` |
| Annual label summary | `data/processed/phase1/segment_year_label_summary.csv` |
| Run summary | `data/processed/phase1/phase1_summary.json` |

## Counts

| Quantity | Count |
|---|---:|
| CEC source lines in study-area bbox | 1,117 |
| 1 km line segments | 11,255 |
| CAL FIRE perimeters in bbox | 800 |
| Segment-year rows | 78,785 |

## Label Totals

| Label | Positive segment-year rows |
|---|---:|
| `all_fire_exposure` | 3,187 |
| `exogenous_fire_exposure` | 2,331 |
| `strict_exogenous_fire_exposure` | 2,075 |
| `electrical_power_fire_overlap` | 885 |

The labels are not mutually exclusive. A segment-year can overlap both
electrical-power and non-electrical fire perimeters in the same year. In the
current output, 29 segment-year rows have both
`electrical_power_fire_overlap = 1` and `exogenous_fire_exposure = 1`.

## Label Interpretation

- `all_fire_exposure`: any fire-perimeter overlap.
- `exogenous_fire_exposure`: overlap with fire perimeters excluding
  `CAUSE = 11` (`Electrical Power`); this is the main validation target.
- `strict_exogenous_fire_exposure`: overlap after excluding `CAUSE = 11` and
  `CAUSE = 2` (`Equipment Use`); this is a sensitivity label.
- `electrical_power_fire_overlap`: overlap with `CAUSE = 11` fire perimeters;
  this is an auxiliary diagnostic, not a calibrated powerline ignition label.

