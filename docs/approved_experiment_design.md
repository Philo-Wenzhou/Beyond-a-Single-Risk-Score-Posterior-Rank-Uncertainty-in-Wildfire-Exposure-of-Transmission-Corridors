# Approved Experiment Design

Canonical source: `../实验设计初步20260630.md`

Status: approved by the project owner on 2026-06-30.

## Core Question

Can fully public, reproducible data be used to build an interpretable,
validatable, and transferable wildfire exposure framework for transmission-line
segments?

The project validates the framework itself, not proprietary operational system
accuracy.

## Two-Level Experiment Design

### Main experiment: external wildfire exposure

Transmission lines are treated as receptor assets. The main task is to identify
which line segments are more likely to be exposed to external wildfire
conditions.

Main validation label:

```text
exogenous_fire_exposure = segment buffer intersects non-electrical fire perimeter
```

with `CAUSE = 11` (`Electrical Power`) excluded.

### Auxiliary experiment: ignition-support diagnostic

The project may also build an optional diagnostic score for
electrical-power-fire overlap:

```text
electrical_power_fire_overlap = segment buffer intersects CAUSE = 11 fire perimeter
```

This diagnostic is not interpreted as calibrated powerline ignition probability.

## Analysis Unit

The approved unit is `segment-year`, not a purely static segment table:

```text
(i, t)
```

where:

- `i`: transmission-line segment;
- `t`: year, initially 2017-2023.

This supports year-specific fire labels and fire-season weather/dryness
summaries.

## Public Data Priority

| Layer | Preferred source | Current status |
|---|---|---|
| Transmission lines | California Energy Commission / CA Open Data | To download; HIFLD exists as fallback |
| Fire perimeters | CAL FIRE FRAP | Downloaded |
| Fire weather / dryness | gridMET | Gap |
| Fuel structure and continuity | LANDFIRE | Gap |
| Terrain | USGS 3DEP DEM | Gap |
| Active fire timing | NASA FIRMS | Optional gap |
| MTBS / WFIGS | MTBS / NIFC WFIGS | Optional robustness |

## Core Labels

```text
y_exo_it    = 1[buffer_i intersects fire perimeter in year t with CAUSE != 11]
y_all_it    = 1[buffer_i intersects any fire perimeter in year t]
y_strict_it = 1[buffer_i intersects fire perimeter in year t with CAUSE not in {11, 2}]
y_elec_it   = 1[buffer_i intersects fire perimeter in year t with CAUSE == 11]
```

## Core Hypotheses

1. Cause screening matters: `y_all` differs materially from `y_exo`.
2. Fuel continuity and dynamic dead-fuel dryness interact positively.
3. Public fuel modules improve exposure discrimination over geometry/weather-only baselines.
4. Bayesian probability and ranking outputs improve calibration and decision usefulness over a deterministic score.
5. Electrical-power-fire overlap may have weak diagnostic signal under wind/dryness conditions, but it is not powerline ignition probability.

## Minimum Publishable Version

Required:

- transmission-line receptor layer;
- CAL FIRE perimeters and `CAUSE=11` screening;
- LANDFIRE fuel structure and continuity;
- gridMET dynamic dryness and wind;
- USGS DEM terrain;
- deterministic public baseline;
- Bayesian external exposure model;
- temporal validation;
- buffer sensitivity;
- ablation study.

Optional:

- FIRMS active-fire timing;
- MTBS / WFIGS cross-checks;
- electrical-power-fire diagnostic model;
- community / building exposure;
- outage or equipment failure data, which remains out of scope.

