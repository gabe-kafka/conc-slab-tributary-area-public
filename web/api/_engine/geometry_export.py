"""Serialize floor_plans geometry data to JSON for frontend canvas rendering."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from shapely.geometry import mapping

from export_column_loads import collect_column_discontinuities


COORD_PRECISION = 4
SIMPLIFY_TOLERANCE = 0.05  # feet


def _round_coords(geojson: Dict) -> Dict:
    """Round all coordinates in a GeoJSON geometry dict to COORD_PRECISION."""

    def _round_ring(ring):
        return [[round(c, COORD_PRECISION) for c in pt] for pt in ring]

    geom_type = geojson.get("type")
    coords = geojson.get("coordinates")
    if coords is None:
        return geojson

    if geom_type == "Point":
        geojson["coordinates"] = [round(c, COORD_PRECISION) for c in coords]
    elif geom_type == "LineString":
        geojson["coordinates"] = _round_ring(coords)
    elif geom_type == "Polygon":
        geojson["coordinates"] = [_round_ring(ring) for ring in coords]
    elif geom_type == "MultiPolygon":
        geojson["coordinates"] = [
            [_round_ring(ring) for ring in polygon] for polygon in coords
        ]
    return geojson


def _serialize_geometry(geom, simplify: bool = True) -> Optional[Dict]:
    """Convert a Shapely geometry to a rounded GeoJSON dict."""
    if geom is None or geom.is_empty:
        return None
    if simplify and hasattr(geom, "simplify"):
        geom = geom.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
    return _round_coords(mapping(geom))


def _serialize_column(
    col_idx: int,
    floor_plan: Dict,
    facade_length_map: Dict[str, float],
    ending_keys: set,
) -> Dict[str, Any]:
    label = floor_plan["column_labels"][col_idx]
    point = floor_plan["column_points"][col_idx]
    footprints = floor_plan.get("column_footprints", [])
    footprint = footprints[col_idx] if col_idx < len(footprints) else None
    region = floor_plan["regions"][col_idx] if col_idx < len(floor_plan.get("regions", [])) else None
    area = floor_plan["areas"][col_idx] if col_idx < len(floor_plan.get("areas", [])) else 0.0

    end_key = (label, round(point.x, 2), round(point.y, 2))

    return {
        "index": col_idx,
        "label": label,
        "point": [round(point.x, COORD_PRECISION), round(point.y, COORD_PRECISION)],
        "footprint": _serialize_geometry(footprint, simplify=False),
        "tributary_region": _serialize_geometry(region),
        "area_sf": round(area, 2),
        "area_sf_ceil": math.ceil(area) if area > 0 else 0,
        "load_areas": _serialize_load_areas(
            floor_plan.get("column_load_areas", []),
            col_idx,
        ),
        "facade_length_ft": round(facade_length_map.get(label, 0.0), 2),
        "ends_here": end_key in ending_keys,
    }


def _serialize_wall(wall_data: Dict) -> Dict[str, Any]:
    return {
        "wall_index": wall_data["wall_index"],
        "wall_line": _serialize_geometry(wall_data.get("wall_line"), simplify=False),
        "tributary_region": _serialize_geometry(wall_data.get("merged_region")),
        "area_sf": round(wall_data.get("total_area", 0.0), 2),
        "area_sf_ceil": math.ceil(wall_data.get("total_area", 0.0)),
        "load_areas": [
            {
                "layer": item.get("layer"),
                "area_sf": round(item.get("area", 0.0), 2),
                "area_sf_ceil": math.ceil(item.get("area", 0.0)),
            }
            for item in wall_data.get("load_areas", [])
            if item.get("area", 0.0) > 1e-6
        ],
    }


def _serialize_beam(beam_data: Dict) -> Dict[str, Any]:
    return {
        "beam_index": beam_data["beam_index"],
        "beam_line": _serialize_geometry(beam_data.get("beam_line"), simplify=False),
        "source_layer": beam_data.get("source_layer", ""),
    }


def _serialize_load_areas(column_load_areas: List, col_idx: int) -> List[Dict[str, Any]]:
    if col_idx >= len(column_load_areas):
        return []

    return [
        {
            "layer": item.get("layer"),
            "area_sf": round(item.get("area", 0.0), 2),
            "area_sf_ceil": math.ceil(item.get("area", 0.0)),
        }
        for item in column_load_areas[col_idx]
        if item.get("area", 0.0) > 1e-6
    ]


def _serialize_load_zones(floor_plan: Dict) -> List[Dict[str, Any]]:
    zones = []
    for index, zone in enumerate(floor_plan.get("load_zones", [])):
        polygon = zone.get("polygon")
        if polygon is None or polygon.is_empty:
            continue
        zones.append({
            "index": index,
            "layer": zone.get("layer"),
            "boundary": _serialize_geometry(polygon, simplify=False),
            "area_sf": round(polygon.area, 2),
            "area_sf_ceil": math.ceil(polygon.area),
        })
    return zones


def _serialize_facade_segments(fascade_data: Optional[Dict]) -> List[Dict]:
    if not fascade_data or not fascade_data.get("segments"):
        return []
    segments = []
    for seg in fascade_data["segments"]:
        coords = seg.get("polyline_points", [])
        segments.append({
            "label": seg.get("label"),
            "type": seg.get("type"),
            "length_ft": round(seg.get("length", 0.0), 2),
            "polyline": [[round(x, COORD_PRECISION), round(y, COORD_PRECISION)] for x, y in coords],
        })
    return segments


def serialize_floor_plans(floor_plans: List[Dict]) -> Dict[str, Any]:
    """Serialize all floor plans to a JSON-serializable dict for the frontend."""
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    discontinuities = collect_column_discontinuities(floor_plans)

    floors = []
    for fp in floor_plans:
        slab = fp.get("slab_polygon")
        if slab is None or slab.is_empty:
            continue

        # Update bounding box
        bounds = slab.bounds  # (minx, miny, maxx, maxy)
        min_x = min(min_x, bounds[0])
        min_y = min(min_y, bounds[1])
        max_x = max(max_x, bounds[2])
        max_y = max(max_y, bounds[3])

        # Facade length map for this floor
        fascade_data = fp.get("fascade_data")
        facade_length_map = fascade_data.get("length_map", {}) if fascade_data else {}

        # Serialize columns
        floor_id = fp.get("floor_number", fp.get("boundary_id", f"FLOOR_{fp['index']}"))
        ending_keys = discontinuities.get(floor_id, set())
        column_count = len(fp.get("column_points", []))
        columns = [
            _serialize_column(i, fp, facade_length_map, ending_keys)
            for i in range(column_count)
        ]

        # Serialize walls
        walls = [_serialize_wall(w) for w in fp.get("walls", [])]
        beams = [_serialize_beam(b) for b in fp.get("beams", [])]

        floors.append({
            "floor_id": floor_id,
            "floor_index": fp["index"],
            "slab_boundary": _serialize_geometry(slab, simplify=False),
            "load_zones": _serialize_load_zones(fp),
            "columns": columns,
            "walls": walls,
            "beams": beams,
            "facade_segments": _serialize_facade_segments(fascade_data),
            "facade_perimeter_ft": round(fascade_data.get("perimeter", 0.0), 2) if fascade_data else 0.0,
        })

    return {
        "floors": floors,
        "bounds": {
            "min_x": round(min_x, COORD_PRECISION) if min_x != float("inf") else 0,
            "min_y": round(min_y, COORD_PRECISION) if min_y != float("inf") else 0,
            "max_x": round(max_x, COORD_PRECISION) if max_x != float("inf") else 0,
            "max_y": round(max_y, COORD_PRECISION) if max_y != float("inf") else 0,
        },
        "floor_count": len(floors),
    }


def export_geometry_json(floor_plans: List[Dict], output_path: str = "geometry.json") -> None:
    """Serialize floor plans and write to a JSON file."""
    data = serialize_floor_plans(floor_plans)
    Path(output_path).write_text(json.dumps(data), encoding="utf-8")
    print(f"\n✓ Geometry JSON export: {output_path} ({len(data['floors'])} floor(s))")
