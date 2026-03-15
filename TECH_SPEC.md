# TECH_SPEC

## Goal
Public web app that wraps the legacy Python pipeline.

Flow:
- DXF in
- tributary-area calculation
- DXF out
- XLSX out

V1 prioritizes legacy parity over new engineering features.

## Fixed Decisions
- Public web app
- No auth in v1
- Async job queue
- Download-only result flow
- Outputs: `DXF + XLSX`
- Intelligent layer mapping with user confirmation
- Legacy parity target: close numeric equivalence with documented differences
- Single hosted environment
- Aggressive file cleanup
- Geometry-based floor assignment
- Boundary-touching columns count as inside
- Wall/slab intersection logic
- Dense `0.1 ft` wall support sampling for Voronoi solve
- `FASCADE` required in v1
- XLSX values rounded up
- Smart unit identification with inch-default assumption
- Low-confidence labels defined as matches over `10 ft`
- Shared-support review triggered by any support touching two polygons
- Openings subtract area; supports inside openings are ignored
- Internal openings do not contribute to `FASCADE`
- Ask for unit confirmation if interpreted floor area exceeds `10,000 sf`

## Stack
- Python 3.12
- FastAPI
- Server-rendered HTML + minimal JS
- Refactored Python engine from legacy scripts
- Redis queue
- Postgres
- Docker
- Job-scoped temporary storage

## Runtime
- `web`: upload, status, downloads
- `worker`: async DXF processing
- `redis`: queue state
- `postgres`: job metadata
- temp storage: uploaded files, intermediate files, artifacts

## Core Flow
1. User uploads one DXF.
2. App inspects layers and proposes semantic mappings.
3. User confirms or overrides mappings.
4. Server creates a job and queues it.
5. Worker validates DXF and normalizes input to the legacy internal contract.
6. Engine resolves units, boundaries, openings, labels, and floor assignments.
7. Engine runs tributary calculation logic.
8. Engine runs `FASCADE` perimeter attribution.
9. Engine builds one canonical result model.
10. Engine renders `tributary_output.dxf` and `column_load_takedown.xlsx`.
11. Result page shows warnings and download links.
12. Files are deleted aggressively after use or timeout.

## Canonical Result Model
All exports must derive from one result object.

Minimum fields:
- `job_id`
- `units`
- `floors[]`
- `warnings[]`
- `artifacts{}`

Each floor should contain:
- `floor_id`
- `columns[]`

Each column/support should contain:
- `label`
- `tributary_area_sf`
- `support_type`

Rule:
- DXF and XLSX must be generated from the same canonical result model.

## Input Contract
- One `.dxf` per job
- V1 defaults to legacy conventions but must support user-selected layer mappings
- Internal normalized units are feet
- Default source-unit assumption is inches
- If interpreted floor area exceeds `10,000 sf`, require unit confirmation

### Supported V1 Inputs
- Boundary geometry: `LINE`, `POLYLINE`, `LWPOLYLINE`, `CIRCLE`, `ARC`
- Column/floor labels: `TEXT`, `MTEXT`
- Column/support points: `POINT`
- Wall-supported edges: required
- Multiple floors in one DXF: required
- Irregular boundaries: required
- Openings / inner loops: required

### Boundary Normalization
- Flatten curves as needed
- Curve flattening must preserve area within about `0.1 sf`
- Auto-heal boundary gaps / near-misses within `1 ft`
- Preserve inner loops as openings
- If any support touches two polygons, require user review

### Intelligent Layer Mapping
The app must infer likely mappings for:
- boundary layers
- wall layers
- point/support layers
- column label layers
- floor label layers

Rules:
- user must confirm or override before processing
- confirmed mapping is stored with the job
- if mapping confidence is too low, require manual mapping before queueing

## Validation

### Hard Fail
- unreadable DXF
- missing required geometry for a supported workflow
- non-computable result
- any support touching two polygons, requiring user review

### Warning But Continue
- missing column labels
- orphaned labels
- duplicate points merged
- missing floor labels
- ignored unsupported entities
- ambiguous associations auto-resolved
- generated fallback labels
- label matches over `10 ft` flagged for review

### Required Behaviors
- missing column labels must not stop processing
- fallback labels must be generated deterministically and include floor identity
- duplicate points must be merged deterministically
- floor assignment must be geometry-based
- edge columns must count as valid supports
- walls must be assigned by slab intersection
- wall support must be approximated with dense `0.1 ft` sampling along the full wall line
- supports inside openings must be ignored
- internal opening edges must be excluded from `FASCADE`

## Outputs

### Required Files
- `tributary_output.dxf`
- `column_load_takedown.xlsx`

### Browser Result
- job status
- warnings summary
- download links

No in-browser CAD preview in v1.

## Interfaces
- `GET /`
- `POST /jobs`
- `GET /jobs/{job_id}`
- `GET /api/jobs/{job_id}`
- `GET /jobs/{job_id}/artifacts/{artifact_name}`

## Job Record
- `id`
- `session_id`
- `status`
- `created_at`
- `updated_at`
- `input_filename`
- `input_path`
- `result_path`
- `layer_mapping_json`
- `warnings_json`
- `error_message`
- `artifacts_json`

Status values:
- `queued`
- `running`
- `failed`
- `completed`

## Engine Structure
- `extract.py`: DXF entity extraction
- `normalize.py`: units, boundary healing, curve flattening, openings, label cleanup, deduplication, floor association, layer normalization
- `compute.py`: tributary calculation with point supports and dense sampled wall supports
- `compute_fascade.py`: perimeter attribution
- `export_dxf.py`: output DXF
- `export_spreadsheet.py`: XLSX export
- `models.py`: canonical result types

The web app must call library code, not shell scripts.

## Validation Strategy
- Golden DXF fixtures from the legacy tool
- Regression checks against legacy outputs
- Compare normalized engineering results, not raw DXF binary equality

Required comparisons:
- extracted points, labels, floors
- tributary areas by floor and label
- warnings
- XLSX worksheet data
- normalized area ownership from DXF output
- layer-mapping normalization behavior
- smart unit detection behavior
- openings and shared-support review behavior

Required tests:
- unit
- integration
- regression
- artifact smoke tests

## Security and Ops
- isolate each job in its own temp workspace
- accept DXF uploads only
- do not execute uploaded content
- rate limit requests
- enforce upload-size limits
- do not expose server paths in UI

## Retention
Target behavior: delete uploaded files and artifacts when the user leaves the result flow.

Because page close/refresh is not reliable server-side, cleanup must be:
- best-effort unload beacon
- delete after successful download when possible
- short TTL fallback for abandoned sessions

Deletion should be favored over retention.

## Deployment
Hosted v1:
- one public web service
- one worker service
- Redis
- Postgres
- temporary artifact storage
- Dockerized deployment

## Open Decisions
- Is CSV needed later in addition to XLSX?
