# PRD

## Product
Two-Way Slab Tributary Area Web App

## Status
Planning only. No implementation started.

## Summary
Web app that takes a DXF, calculates two-way slab tributary areas, and returns:
- a DXF with tributary areas illustrated
- a spreadsheet-friendly tributary area output matching the DXF

Version 1 is a web-packaged version of the legacy Python tool:
[Voronoi-Column-Takedown](https://github.com/gabe-kafka/Voronoi-Column-Takedown)

## Users
- Structural engineers working with two-way slabs

## Problem
Engineers need tributary areas before creating column load takedowns. Manual CAD workflows are slow and inconsistent. The current tool works locally for one user but is not packaged for broader use.

## Goals
- Generate a tributary DXF
- Generate a spreadsheet-friendly tributary table
- Preserve legacy tool behavior for supported inputs
- Make the workflow usable by others through a web app
- Be at least as fast as doing this work by hand for normal cases
- Be stable on supported edge cases

## Non-Goals
- Full structural design
- Full column load takedown calculations
- Replacing engineer judgment
- Supporting every slab geometry or CAD standard in v1
- Rewriting the engineering logic from scratch unless needed

## Primary Use Case
1. Engineer receives architectural plans.
2. Engineer needs tributary areas before column load takedown.
3. Engineer submits a DXF to the app.
4. App calculates tributary areas.
5. App returns:
   - tributary DXF
   - spreadsheet output usable for column load takedown

## Requirements

### Inputs
- Must be a web app
- Must accept DXF input
- Must support the practical input conventions used by the legacy tool in v1
- Must reject or warn on malformed or unsupported inputs

### Calculation
- Must calculate two-way slab tributary area allotment for supported cases
- Must match legacy behavior on benchmark inputs, or document intentional differences
- Must produce deterministic results for the same input
- Must remain stable for supported edge cases

### Outputs
- Must generate a DXF with tributary areas illustrated
- Must generate a spreadsheet output that corresponds to the DXF
- Spreadsheet output must be usable in a column load takedown workflow
- Should support easy copy/paste into spreadsheet software
- Should support downloadable spreadsheet output

### Reviewability
- Users must be able to map tributary areas to columns or supports
- DXF and spreadsheet outputs must correspond clearly
- Warnings must be shown when labels, floors, supports, or boundaries are ambiguous

## Scope

### V1 In Scope
- Package the legacy Python tool as a web app
- Preserve the DXF to DXF plus spreadsheet workflow
- Deliver files through the browser
- Preserve the current engineering utility

### V1 Out of Scope
- Major expansion beyond legacy-supported geometry
- New engineering analysis modules unrelated to tributary areas
- Full office workflow automation after this step
- Replacing CAD or spreadsheet software

## Success Criteria
- The product is usable by others as a web app
- It does what the legacy tool did for supported cases
- DXF and spreadsheet outputs correspond correctly
- Engineers can use the spreadsheet output in downstream load takedown work
- Benchmark outputs are accepted as equivalent to the legacy tool
- Normal workflows are no slower than doing the work by hand
- Supported edge cases behave reliably

## Constraints
- Must be a web app
- Legacy repo is the v1 baseline
- V1 should prioritize migration and packaging over major new features
- Users must still provide drawings that meet supported input conventions

## Risks
- Legacy assumptions may be undocumented
- CAD input conventions may be brittle
- Web app output parity may be difficult on edge cases
- Users may over-assume supported conditions
- Trust will drop if DXF and spreadsheet outputs diverge

## Open Questions
- Which DXF conventions from the legacy tool are mandatory in v1?
- Which edge cases are required for launch?
- Is spreadsheet output required as Excel, copyable table, or both?
- Does v1 need in-browser preview, or are downloads enough?
- Is v1 internal, public, or client-facing?
