# Label and Overlap Audit

The main label remains external/exogenous exposure:

`y_exo = 1` when a segment buffer intersects a CAL FIRE perimeter whose
perimeter-level cause is not Electrical Power (`CAUSE != 11`).

Electrical-power overlap is retained only as a diagnostic label. It is not an
ignition-probability label, not an outage label, and not a responsibility label.

Observed label counts in the segment-year table:

- all-fire exposure positives: 3187
- exogenous exposure positives: 2331
- strict exogenous positives: 2075
- electrical-power overlap positives: 885
- rows with both exogenous and electrical-power overlap: 29
