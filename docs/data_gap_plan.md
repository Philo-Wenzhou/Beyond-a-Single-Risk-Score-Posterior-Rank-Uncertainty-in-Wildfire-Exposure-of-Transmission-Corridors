# Data and Gap Plan

## Study Boundary

This project estimates wildfire exposure of transmission-line segments as
externally exposed linear assets.

It does not estimate:

- powerline-caused ignition probability;
- equipment failure probability;
- outage probability;
- legal or operational responsibility for ignition.

The asset layer is treated as a replaceable receptor interface. The same hazard
pipeline should later support roads, evacuation corridors, substations,
communication towers, communities, or protected-area boundaries.

## Current Local Data

| Data layer | Local status | Analysis role | Key fields |
|---|---|---|---|
| Transmission lines | HIFLD downloaded; CEC preferred source still needed | Asset receptor layer | voltage/kV, owner, status, type, geometry |
| CAL FIRE perimeters | Downloaded, 2017-2023 | Historical exposure labels and validation | `YEAR_`, `CAUSE`, `FIRE_NAME`, `GIS_ACRES`, geometry |
| County boundaries | Downloaded | California boundary and clipping | `STATEFP`, `COUNTYFP`, geometry |
| CAL FIRE cause summary | Generated | Causal-boundary screening | `CAUSE`, cause name, count, acres |

## Critical Cause Finding

CAL FIRE `CAUSE = 11` is `Electrical Power`.

For 2017-2023:

- electrical-power fires: 160;
- electrical-power burned area: 1,321,109.83 acres;
- largest examples include Dixie 2021, Camp 2018, Woolsey 2018, and Kincade 2019.

These fires should not be mixed uncritically into the main exposure-validation
label if the manuscript treats transmission lines only as external receptors.

## Planned Validation Labels

| Label | Definition | Main use |
|---|---|---|
| `all_fire_exposure` | segment buffer intersects any fire perimeter in year `t` | robustness check |
| `exogenous_fire_exposure` | segment buffer intersects year-`t` fire perimeters after excluding `CAUSE = 11` | main validation label |
| `strict_exogenous_fire_exposure` | excludes `CAUSE = 11` and optionally `CAUSE = 2` | sensitivity analysis if reviewers challenge broader equipment causes |
| `electrical_power_fire_overlap` | segment buffer intersects year-`t` fire perimeters with `CAUSE = 11` | auxiliary diagnostic, not calibrated ignition probability |

## Data Gaps

| Gap | Required dataset | Priority | Why it matters |
|---|---|---:|---|
| Preferred line layer | California Energy Commission transmission lines | High | Approved design uses CEC / CA open data as the public receptor layer; HIFLD remains fallback |
| Dynamic fire weather | gridMET daily variables | High | Needed for wind, humidity, VPD, ERC/BI, dead-fuel moisture proxies |
| Fuel and vegetation | LANDFIRE fuel model / vegetation | High | Needed for fuel continuity and physics-informed spread potential |
| Terrain | SRTM or USGS DEM | High | Needed for slope, aspect, and terrain-driven spread potential |
| Active fire timing | NASA FIRMS MODIS/VIIRS | Medium | Helps distinguish active-fire evidence from perimeter-only labels |
| Building/community exposure | Microsoft Buildings / Census | Medium | Optional consequence weighting |
| Lightning | NLDN is restricted; public alternatives may be coarse | Low for first paper | Useful for cause-specific ignition modeling, not required for exposure ranking |
| Outage/equipment failures | Usually proprietary | Out of scope | Would shift the study from exposure to failure risk |

## Recommended First Study Area

Northern Sierra / Southern Cascades, California:

```text
lon: -123.2 to -119.0
lat:  38.6 to   41.8
```

Rationale:

- multiple major 2017-2023 fires;
- dense mountain transmission corridors;
- strong wind and fuel-moisture relevance;
- manageable data volume;
- close fit to external wildfire exposure of linear infrastructure.

## Data Readiness Gate

Before Bayesian modeling, produce one model-ready `segment-year` panel with:

- segment geometry and length;
- buffer geometry;
- year;
- `all_fire_exposure`;
- `exogenous_fire_exposure`;
- `strict_exogenous_fire_exposure`;
- `electrical_power_fire_overlap`;
- nearest / intersecting fire attributes;
- static susceptibility fields;
- annual fire-season dynamic weather fields;
- deterministic baseline score;
- posterior samples or summarized Bayesian outputs.
