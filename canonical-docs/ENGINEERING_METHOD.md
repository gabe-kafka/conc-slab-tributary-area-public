# ENGINEERING_METHOD

## Goal
Document the v1 engineering method. It is legacy-derived, but updated where you chose more robust behavior.

## Scope
Legacy tool:
- reads one DXF
- identifies floors, columns, labels, and walls
- computes tributary regions
- outputs a tributary DXF
- outputs an XLSX matrix

Not included:
- code checks
- reinforcement design
- load combinations
- punching, deflection, or full structural design

## Units
- default source DXF assumption: inches
- internal geometry converted to feet
- areas computed in square feet
- displayed/exported areas rounded up with `ceil`
- if interpreted floor area exceeds `10,000 sf` per floor, flag for unit confirmation

## Legacy Inputs
- `POINT`: column/support points
- `LINE`, `LWPOLYLINE`: slab boundary inputs
- `LINE`, `LWPOLYLINE` on `WALL`: wall supports
- `MTEXT` on `COLUMN NUMBER`: column labels
- `TEXT` or `MTEXT` on `FLOOR NUMBER`: floor labels

Important legacy behavior:
- all `POINT` entities are treated as candidate columns/supports
- column labels are only read from `MTEXT` on `COLUMN NUMBER`
- floor labels are read from `TEXT` and `MTEXT` on `FLOOR NUMBER`

## Slab Boundary Reconstruction
V1 must be robust across common CAD inputs.

Supported boundary inputs:
- `LINE`
- `LWPOLYLINE`
- `POLYLINE`
- `ARC`
- `CIRCLE`

Rules:
- flatten curved geometry when needed
- flattening tolerance should keep area error to about `0.1 sf`
- auto-heal small gaps / near-misses with `1 ft` snap tolerance
- detect and preserve openings / inner loops
- if any support touches two polygons, require user review

## Floor Identification
- use geometry-based floor assignment, not legacy vertical/Y heuristic
- each floor polygon gets the nearest floor label
- if no floor label exists, fall back to generated floor identity
- merge polygons with the same floor identity using `unary_union`

## Column Point Handling

### Deduplication
- merge raw points within `0.25 ft`
- keep first point as canonical
- record later points as duplicates

### Floor Assignment
- a column on the slab edge counts as inside
- use boundary-tolerant containment, not strict `contains()`
- if any support touches two polygons, require user review
- unassigned columns are excluded

## Wall Handling
- use only `LINE` and `LWPOLYLINE` on `WALL`
- convert each wall to `LineString`
- use wall/slab intersection logic for floor assignment
- sample each wall every `0.1 ft` to approximate continuous line support in the Voronoi solve
- walls intersecting multiple slab regions require user review

## Column Label Handling

### Normalization
- strip DXF formatting noise
- collapse whitespace
- remove spaces, underscores, hyphens
- remove non-alphanumeric characters
- uppercase

Examples:
- `5a` -> `5A`
- `5-A` -> `5A`
- `7  B` -> `7B`

### Association
Per floor:
- keep labels within `50 ft` buffer of slab polygon
- compute all label-to-point distances
- sort candidate pairs by distance
- greedily assign nearest unused label to nearest unused point

### Tolerances
- initial label radius: `10 ft`
- auto-expand: `true`
- max radius: `35 ft`
- min step: `5 ft`
- may jump to `nearest_remaining_distance + 0.5 ft`

### Unlabeled Results
- unassigned points get generated floor-based labels
- far labels remain orphan warnings
- labels over `10 ft` away are low-confidence and should be surfaced for review

## Tributary Area Method

### Support Set
Per floor, combine:
- column points
- densely sampled wall support points

### Region Solve
For each support entity:
- start with slab polygon
- apply point-point and point-line / line-line proximity boundaries as needed
- intersect current region with that half-plane
- stop if region becomes empty

Result:
- slab-clipped Voronoi-style tributary region for each support entity

### Bounding Box
- use slab bounds expanded by `5 ft` on all sides for half-plane construction

### Area
- area = Shapely polygon area of final region
- raw values stay floating-point
- report values commonly use rounded-up whole square feet

## Wall Tributary Areas
- each wall's sampled support points get tributary regions from the same combined solve
- merge non-empty regions belonging to the same wall with `unary_union` if needed
- merged area is wall tributary area

## Large Tributary Threshold
- `30 sf`
- presentation only
- does not affect calculation

## Perimeter Attribution (`FASCADE`)
Separate from tributary area.

Method:
- use slab exterior as perimeter line
- select nearby columns/walls within `2 ft`
- if none found, expand by `1 ft` up to `15 ft`
- sample perimeter at `0.5 ft`
- assign each sampled segment to nearest candidate
- sum assigned lengths by label
- if multiple touching slabs exist, treat the inner polygon as façade and assume exterior-adjacent balcony condition
- internal openings do not count as façade

## Outputs

### DXF
- copy original DXF entities where possible
- preserve original coordinates
- add result layers

Key layers:
- `FLOOR_{i}_TRIBUTARY_COL_{j}`
- `FLOOR_{i}_WALL_TRIBUTARY_{k}`
- `FLOOR_{i}_LARGE_TRIBUTARY`
- `FLOOR_{i}_AREA_LABELS`

Area labels:
- placed at region centroid
- shown as rounded-up whole square feet, e.g. `123 SF`

### XLSX
Sheets:
- `MASTER TRIBUTARY AREA`
- `FASCADE LENGTH`

`MASTER TRIBUTARY AREA`:
- rows = floors
- columns = column labels
- values = rounded-up tributary areas
- floors sorted by custom roof/main/basement/number heuristic
- columns sorted alphanumerically

`FASCADE LENGTH`:
- rows = floors
- columns = column/wall labels near perimeter
- values = rounded-up perimeter lengths

## Openings
- openings / inner loops subtract from slab area
- columns and walls inside openings are ignored
- internal opening edges are excluded from `FASCADE`

## Chosen V1 Changes vs Legacy
- replace floor Y-heuristic with nearest-floor-label geometry assignment
- count edge columns as valid supports
- replace wall centroid assignment with wall/slab intersection logic
- use dense `0.1 ft` wall sampling for the Voronoi solve
- support robust CAD cleanup, openings, and flattened curves
- use floor-based generated labels
- keep `FASCADE` in scope
- keep rounded-up XLSX outputs
- keep smart inch-default unit identification

## Baseline Rule
Web app v1 should preserve legacy behavior where practical, but the choices above override known weak legacy heuristics.
