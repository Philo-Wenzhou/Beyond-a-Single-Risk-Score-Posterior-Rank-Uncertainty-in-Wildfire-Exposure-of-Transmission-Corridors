# Figure Style Guide

## Phase 1 SCI Map Style

Current script:

```text
scripts/make_sci_phase1_figures.py
```

Output:

```text
outputs/figures/sci_phase1/
```

## Basemap

Use a light, low-contrast basemap:

```text
CartoDB Positron
```

The basemap should remain background context. It is rendered with reduced alpha
so transmission-line labels and fire-perimeter overlays remain dominant.

## Color Roles

| Role | Color | Purpose |
|---|---|---|
| Exogenous exposure | deep blue `#005f73` | main validation target |
| Electrical diagnostic | amber-brown `#c27a15` | auxiliary diagnostic / CAUSE = 11 |
| Strict exogenous | muted green `#4b7f2c` | sensitivity label |
| All fire exposure | dark grey `#4d5256` | unscreened comparison |
| Other transmission lines | neutral grey-blue `#4f5961` | context |
| Non-electrical fire perimeters | neutral grey | fire context without overpowering line labels |

Avoid high-saturation red/purple palettes. Use a white legend box with a subtle
grey border when plotted over a basemap.

## Cartographic Rules

- Do not draw the projected study-area rectangle as a slanted frame.
- Use the axis/neatline as the map frame.
- Keep the basemap visible but subdued.
- Label source line should cite CEC, CAL FIRE FRAP, and CartoDB Positron when
  basemap tiles are used.
- Export both PNG and PDF.

