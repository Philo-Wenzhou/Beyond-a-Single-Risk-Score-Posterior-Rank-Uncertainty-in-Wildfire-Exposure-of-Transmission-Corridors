# CAL FIRE Cause Field Analysis

CAL FIRE `CAUSE` is a coded field. The public FeatureServer metadata defines
`CAUSE = 11` as `Electrical Power`.

For the downloaded 2017-2023 California historic fire perimeter dataset:

| Cause code | Cause name | Fire count | GIS acres |
|---:|---|---:|---:|
| 14 | Unknown / Unidentified | 1,046 | 2,517,648.69 |
| 1 | Lightning | 415 | 4,712,769.54 |
| 2 | Equipment Use | 317 | 136,724.79 |
| 9 | Miscellaneous | 289 | 1,275,542.71 |
| 10 | Vehicle | 233 | 468,526.43 |
| 11 | Electrical Power | 160 | 1,321,109.83 |
| 7 | Arson | 138 | 99,712.86 |
| 5 | Debris | 106 | 58,923.95 |
| 4 | Campfire | 52 | 46,395.82 |
| 8 | Playing with Fire | 25 | 7,934.29 |
| 18 | Escaped Prescribed Burn | 17 | 1,934.12 |
| 3 | Smoking | 14 | 999.65 |
| 15 | Structure | 12 | 1,568.71 |
| 6 | Railroad | 3 | 244.12 |
| 16 | Aircraft | 2 | 3.07 |

Largest `Electrical Power` fires include Dixie 2021, Camp 2018, Woolsey 2018,
and Kincade 2019. These fires are scientifically important but create a
causal-boundary issue if transmission lines are treated only as externally
exposed receptors.

## Recommended Treatment

Use two validation labels:

1. `all_fire_exposure`: segment buffer intersects any 2017-2023 fire perimeter.
2. `exogenous_fire_exposure`: segment buffer intersects fire perimeters after
   excluding `CAUSE = 11` (`Electrical Power`).

The main manuscript should emphasize `exogenous_fire_exposure` when arguing
that the asset layer is a replaceable receptor interface rather than an ignition
source. The `all_fire_exposure` label can be retained as a robustness check.

`CAUSE = 2` (`Equipment Use`) should not be automatically treated as powerline
ignition, because it is broader than electrical-power ignitions. It can be
excluded in a stricter sensitivity test if reviewers challenge the causal
boundary.

