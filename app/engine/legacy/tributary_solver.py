from __future__ import annotations

import math
from typing import Dict, List, Tuple

from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import unary_union, voronoi_diagram

WALL_SUPPORT_SPACING_FEET = 1.0
SITE_KEY_PRECISION = 6
VORONOI_PADDING_FEET = 5.0
CELL_EPSILON = 1e-7


WALL_COLUMN_CLEARANCE_FEET = 2.0  # skip wall support points within this distance of a column


def sample_wall_support_points(
    wall_line,
    spacing: float = WALL_SUPPORT_SPACING_FEET,
    column_points: List[Point] | None = None,
) -> List[Point]:
    if wall_line is None or wall_line.length <= 0:
        return []

    spacing = max(spacing, 0.25)
    total_length = wall_line.length
    support_points: List[Point] = []
    distance = 0.0

    while distance < total_length - 1e-9:
        support_point = wall_line.interpolate(distance)
        pt = Point(support_point.x, support_point.y)
        if not _too_close_to_column(pt, column_points):
            support_points.append(pt)
        distance += spacing

    end_point = Point(wall_line.coords[-1])
    if not _too_close_to_column(end_point, column_points):
        if not support_points or support_points[-1].distance(end_point) > CELL_EPSILON:
            support_points.append(end_point)

    return support_points


def _too_close_to_column(pt: Point, column_points: List[Point] | None) -> bool:
    if not column_points:
        return False
    return any(pt.distance(cp) < WALL_COLUMN_CLEARANCE_FEET for cp in column_points)


def solve_floor_tributary(floor_plan: Dict, threshold: float = 30.0) -> Dict:
    floor_idx = floor_plan["index"]
    boundary_id = floor_plan["boundary_id"]
    slab_polygon = floor_plan["slab_polygon"]
    column_points = floor_plan.get("column_points", [])
    walls = floor_plan.get("walls", [])

    logs = [
        f"",
        f"--- Floor {floor_idx} ({boundary_id}) ---",
        f"Columns: {len(column_points)}",
        f"Walls: {len(walls)}",
    ]

    combined_points: List[Point] = list(column_points)
    wall_ranges: List[Tuple[int, int, int]] = []

    for wall_data in walls:
        wall_idx = wall_data["wall_index"]
        support_points = wall_data.get("support_points", [])
        start = len(combined_points)
        combined_points.extend(support_points)
        end = len(combined_points)
        wall_ranges.append((wall_idx, start, end))

    total_support_points = sum(len(wall.get("support_points", [])) for wall in walls)
    column_count = len(column_points)

    if not combined_points:
        logs.append("No points found - skipping tributary calculation")
        return {
            "index": floor_idx,
            "column_regions": [],
            "column_areas": [],
            "wall_results": {},
            "logs": logs,
        }

    regions, unique_site_count = _clipped_voronoi_regions(slab_polygon, combined_points)
    logs.append(
        f"Total points for tributary calculation: {unique_site_count} unique "
        f"({column_count} columns + {total_support_points} wall supports)"
    )

    column_regions = regions[:column_count]
    column_areas = [region.area for region in column_regions]

    logs.append(f"Tributary regions calculated: {len(regions)}")
    large_area_idxs = [index for index, area in enumerate(column_areas) if area > threshold]
    logs.append(f"Large column tributary areas (>{threshold} SF): {len(large_area_idxs)}")

    if large_area_idxs:
        logs.append("Large column tributary areas (sorted by size):")
        for rank, idx in enumerate(sorted(large_area_idxs, key=lambda item: column_areas[item], reverse=True), 1):
            col_point = column_points[idx]
            logs.append(
                f"  {rank}. Column {idx} at ({col_point.x:.2f}, {col_point.y:.2f}): "
                f"{math.ceil(column_areas[idx]):.0f} SF"
            )

    logs.append("")
    logs.append("--- Wall Tributary Regions ---")

    wall_results: Dict[int, Dict] = {}
    for wall_idx, start, end in wall_ranges:
        wall_regions = [region for region in regions[start:end] if not region.is_empty]
        if not wall_regions:
            logs.append(f"Wall {wall_idx}: No tributary regions")
            wall_results[wall_idx] = {"merged_region": None, "total_area": 0.0}
            continue

        try:
            merged_region = unary_union(wall_regions)

            total_area = merged_region.area if merged_region is not None and not merged_region.is_empty else 0.0
            wall_results[wall_idx] = {"merged_region": merged_region, "total_area": total_area}
            logs.append(f"Wall {wall_idx}: {len(wall_regions)} regions merged, Total area: {math.ceil(total_area):.0f} SF")
        except Exception as exc:
            wall_results[wall_idx] = {"merged_region": None, "total_area": 0.0}
            logs.append(f"Warning: Could not merge tributary regions for wall {wall_idx}: {exc}")

    return {
        "index": floor_idx,
        "column_regions": column_regions,
        "column_areas": column_areas,
        "wall_results": wall_results,
        "logs": logs,
    }


def _clipped_voronoi_regions(slab_polygon, points: List[Point]) -> Tuple[List, int]:
    if len(points) == 1:
        return [slab_polygon], 1

    canonical_points, mapping = _dedupe_points(points)
    if len(canonical_points) == 1:
        return [slab_polygon for _ in points], 1

    envelope = slab_polygon.envelope.buffer(VORONOI_PADDING_FEET)
    diagram = voronoi_diagram(MultiPoint([(point.x, point.y) for point in canonical_points]), envelope=envelope, edges=False)
    cells = list(getattr(diagram, "geoms", [diagram]))
    canonical_regions: List = [Polygon() for _ in canonical_points]
    unmatched = set(range(len(canonical_points)))

    for cell in cells:
        if cell.is_empty:
            continue

        clipped = cell.intersection(slab_polygon)
        if clipped.is_empty:
            continue

        matched_index = None
        buffered = cell.buffer(CELL_EPSILON)
        for site_index in list(unmatched):
            if buffered.covers(canonical_points[site_index]):
                matched_index = site_index
                unmatched.remove(site_index)
                break

        if matched_index is None:
            reference = clipped.representative_point()
            search_space = unmatched or set(range(len(canonical_points)))
            matched_index = min(search_space, key=lambda idx: canonical_points[idx].distance(reference))
            unmatched.discard(matched_index)

        canonical_regions[matched_index] = clipped

    return [canonical_regions[index] for index in mapping], len(canonical_points)


def _dedupe_points(points: List[Point]) -> Tuple[List[Point], List[int]]:
    canonical_points: List[Point] = []
    mapping: List[int] = []
    key_to_index: Dict[Tuple[float, float], int] = {}

    for point in points:
        key = (round(point.x, SITE_KEY_PRECISION), round(point.y, SITE_KEY_PRECISION))
        index = key_to_index.get(key)
        if index is None:
            index = len(canonical_points)
            key_to_index[key] = index
            canonical_points.append(point)
        mapping.append(index)

    return canonical_points, mapping
