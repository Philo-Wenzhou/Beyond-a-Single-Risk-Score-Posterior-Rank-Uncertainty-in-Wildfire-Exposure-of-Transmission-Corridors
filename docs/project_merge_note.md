# Project Merge Note

Date: 2026-06-30

## Decision

`Bayesian_Wildfire_Exposure_CA` is the unified active project directory.

It is retained as the main workspace because it already contains the downloaded
entity data and completed Phase 1 outputs:

- CEC transmission lines;
- CAL FIRE fire perimeters;
- HIFLD fallback transmission lines;
- Census county boundary data;
- 1 km transmission-line segments;
- 1 km segment buffers;
- 2017-2023 segment-year exposure labels;
- publication-style Phase 1 figures.

## Merged Source

`public_wildfire_line_exposure` is treated as a clean public-pipeline template.
Its configuration and scripts have been copied into:

```text
public_pipeline/
```

The `.venv` directory and duplicate raw data from `public_wildfire_line_exposure`
were not copied. This avoids unnecessary duplication while preserving the
cleaner configuration and script organization for future refactoring.

## Current Roles

| Location | Role |
|---|---|
| `data/raw/` | downloaded entity data used by the active project |
| `data/processed/phase1/` | completed Phase 1 segment and label outputs |
| `scripts/` | active scripts used for current analysis |
| `outputs/figures/` | active rendered figures |
| `docs/` | project decisions, analysis framework, data inventory, outputs |
| `public_pipeline/` | imported clean public-data pipeline template |

## Operating Rule

Continue active analysis in `Bayesian_Wildfire_Exposure_CA`. Use
`public_pipeline/` only as a source of structure or refactoring ideas unless a
script is explicitly promoted into the active `scripts/` directory.

