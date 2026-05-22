# Cross-Section Label Accuracy — Plan

## Issues confirmed by audit on demo 3 (550 footprints)

| # | Issue | Severity | Action |
|---|---|---|---|
| 1 | Diamonds (rotated squares) labelled by MRR side, e.g. 14×14 from diamond w/ 14.14" edges | **Keep current** (user confirmed) | None |
| 2 | Non-convex shapes (L, T, +) labelled by MRR bbox, losing real dims | Wrong | Tag `L24x26` (or similar) when polygon area / bbox area < 0.85, hull area / area > 1.10 |
| 3 | Triangle / pentagon / hexagon labelled as MRR rectangle | Wrong | Prefix `tri`, `pent`, `hex`, then bbox dims |
| 4 | Octagons (circularity ≈ 0.948) classify as circles | Bug — threshold too loose | Raise circle threshold from 0.92 → 0.96; tag `oct<dia>` for 8-vertex polygons in [0.92, 0.96] |
| 5 | CIRCLE entity discretized to N-pt polygon under-reports area by ≤ 0.5% | Minor | Trust `CIRCLE` entity radius directly when available (already in audit ground-truth path; promote to prod) |
| 6 | 4-vertex polygons with one stray vertex inflate MRR bbox | Edge case | Detect via convex-hull-area / poly-area ratio; flag in audit; no auto-fix |
| 7 | Same dimension across different shape types reads identical | Cosmetic | Shape tag from #2-#4 handles this |

## Proposed `format_cross_section` algorithm

```
1. If footprint empty → None
2. If source entity is CIRCLE → d<2*radius>          (new shortcut)
3. n = unique vertex count
4. is_convex = poly.equals(poly.convex_hull)
5. If n == 4 and looks_like_rectangle → MRR sides           (existing path)
6. If circularity ≥ 0.96 → d<dia from area>                 (raised threshold)
7. If n == 8 and circularity in [0.92, 0.96) → oct<bbox>    (new)
8. If n in {3, 5, 6} → <tri|pent|hex><bbox>                  (new)
9. If not is_convex → L<bbox>                                (new — covers L, T, +, U)
10. Else fall back to MRR (current behaviour)
```

## Harness design

Single script `web/api/_engine/audit_cross_sections.py` (rebuild existing).

Inputs:
- DXF path
- Layer mapping (or default `{support_point: ["COLS"]}`)

Per-footprint row (CSV):
- `dxftype`, `handle`, `layer`
- `n_vertices`, `is_convex`, `area_in2`, `perimeter_in`, `circularity`
- `bbox_w_in`, `bbox_h_in`, `mrr_w_in`, `mrr_h_in`
- `current_label` (production `format_cross_section`)
- `proposed_label` (new algorithm)
- `shape_class` (rect | diamond | circle | octagon | triangle | pentagon | hexagon | L_shape | other)
- `anomaly` (free-text: "stray_vertex", "bumped_edge", "mrr≠bbox", etc.)

Summary (printed):
- Distribution by `shape_class`
- Distribution of current vs proposed labels
- Count of changed labels (current → proposed)
- Top anomalies

## Acceptance criteria

- Zero non-convex columns labelled as plain rectangles.
- Zero octagons labelled as circles.
- Triangles / pentagons / hexagons carry a shape tag.
- Rectangles + diamonds + true circles produce the same label as today (no regression).
- Per-footprint CSV exists for the demo with `current_label` and `proposed_label` columns so human can scan changes.
