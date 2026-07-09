# Execution Roadmap

## Phase 0: Done

- Created project folder.
- Downloaded HIFLD transmission lines.
- Downloaded CAL FIRE 2017-2023 fire perimeters.
- Downloaded US Census county boundaries.
- Parsed CAL FIRE `CAUSE` metadata.
- Generated cause summary tables.
- Approved canonical experiment design in `实验设计初步20260630.md`.

## Phase 1: Public Line Layer, Geometry, and Labels

Status: done for the main 1 km segment / 1 km buffer design.

Goal: create a clean `segment-year` exposure panel.

Tasks:

1. download California Energy Commission transmission lines;
2. retain HIFLD as a fallback / cross-check line source;
3. extract California boundary from Census counties;
4. clip lines to Northern Sierra / Southern Cascades candidate bbox;
5. split lines into fixed-length segments, with 1 km as the main scale;
6. create segment buffers, with 1 km as the main buffer;
7. expand to segment-year rows for 2017-2023;
8. intersect buffers with CAL FIRE perimeters by year;
9. generate:
   - `all_fire_exposure`;
   - `exogenous_fire_exposure`;
   - `strict_exogenous_fire_exposure`;
   - `electrical_power_fire_overlap`.

Output:

```text
data/processed/phase1/study_area_northern_sierra_southern_cascades.gpkg
data/processed/phase1/segments_1km.gpkg
data/processed/phase1/segment_buffers_1km.gpkg
data/processed/phase1/segment_year_labels_2017_2023.csv
data/processed/phase1/segment_year_label_summary.csv
```

Completed counts:

- CEC lines in study-area bbox: 1,117;
- 1 km line segments: 11,255;
- CAL FIRE perimeters in bbox: 800;
- segment-year rows: 78,785;
- `all_fire_exposure`: 3,187 positive rows;
- `exogenous_fire_exposure`: 2,331 positive rows;
- `strict_exogenous_fire_exposure`: 2,075 positive rows;
- `electrical_power_fire_overlap`: 885 positive rows.

## Phase 2: Static Susceptibility

Goal: attach static predictors.

Tasks:

1. download/crop DEM;
2. compute slope and aspect;
3. download/crop LANDFIRE or interim land-cover proxy;
4. calculate fuel continuity around each segment;
5. calculate historical fire proximity and frequency;
6. add voltage/consequence fields from CEC, falling back to HIFLD if needed.

Output:

```text
data/processed/segment_static_susceptibility.parquet
```

## Phase 3: Dynamic Fire Weather

Goal: attach weather and fire-danger predictors.

Tasks:

1. choose gridMET variables;
2. download for 2017-2023 and selected bbox;
3. extract segment-level daily values;
4. compute wind percentile, VPD percentile, dry-day indicators;
5. summarize by fire season and alarm dates.

Output:

```text
data/processed/segment_dynamic_weather_daily.parquet
data/processed/fire_cause_weather_table.csv
```

## Phase 4: Deterministic Baseline

Goal: build a transparent comparator.

Tasks:

1. normalize static and dynamic predictors;
2. define deterministic score;
3. choose threshold `tau`;
4. evaluate against `exogenous_fire_exposure`;
5. retain Model 0 geometry-only baseline for comparison.

Output:

```text
data/processed/deterministic_segment_year_scores.parquet
outputs/figures/deterministic_score_map.png
```

## Phase 5: Bayesian External Exposure Model

Goal: fit the approved Bayesian segment-year exposure model.

Tasks:

1. fit Model 2 against `exogenous_fire_exposure`;
2. include county and year random effects;
3. include the fuel-continuity by dryness interaction;
4. compare against Model 0 and deterministic baseline;
5. compute:
   - `P(exposure > tau)`;
   - `P(rank in top 10%)`;
   - posterior mean;
   - posterior credible interval;
6. compare with deterministic ranking.

Output:

```text
data/processed/bayesian_segment_year_exposure.parquet
outputs/figures/posterior_exceedance_map.png
outputs/figures/rank_stability_map.png
```

## Phase 6: Validation and Sensitivity

Goal: prove the public-data framework is valid, not just visually plausible.

Tasks:

1. label boundary comparison: `all`, `exo`, `strict`, `elec`;
2. temporal holdout: train 2017-2021, test 2022-2023;
3. spatial validation: county leave-one-out or spatial blocks;
4. buffer sensitivity: 250 m, 500 m, 1000 m, 2000 m;
5. fuel-module ablation: M0-M6;
6. optional electrical-power-fire overlap diagnostic.

Output:

```text
outputs/tables/validation_metrics.csv
outputs/figures/ablation_performance.png
outputs/figures/calibration_curve.png
outputs/figures/top_decile_capture.png
```

## Phase 7: Preprint Draft

Goal: turn the pipeline into a methods preprint.

Sections:

1. Introduction: deterministic risk maps are insufficient for extreme-disaster decisions.
2. Data: public California wildfire, infrastructure, weather, fuel, terrain layers.
3. Methods: segment-year panel, cause screening, fuel/dryness/terrain modules.
4. Results: posterior external exposure and ranking validation.
5. Sensitivity: buffer, temporal/spatial validation, ablation, electrical-power diagnostic.
6. Discussion: asset-agnostic extension to roads, communities, substations.
