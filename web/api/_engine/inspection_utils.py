"""DXF inspection utilities adapted for in-memory processing (no filesystem writes)."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Dict, List

import ezdxf
from shapely.ops import unary_union

from geometry_utils import build_floor_surfaces, polygons_from_entities

ROLE_KEYWORDS = {
    "boundary": ["boundary", "slab", "outline", "perimeter", "deck", "edge"],
    "wall": ["wall", "shear", "core"],
    "support_point": ["point", "pts", "support", "column center", "column pt"],
    "column_label": ["column number", "col no", "column id", "column label", "column"],
    "floor_label": ["floor number", "level", "story", "storey", "floor"],
}


def inspect_dxf_bytes(payload: bytes, filename: str) -> Dict:
    """Parse DXF from bytes and return draft metadata dict."""
    # ezdxf.read() expects a text stream; write to temp file and use readfile
    tmp = Path(tempfile.mktemp(suffix=".dxf"))
    try:
        tmp.write_bytes(payload)
        doc = ezdxf.readfile(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    layer_counts = _layer_counts(doc)
    layers = sorted({layer.dxf.name for layer in doc.layers} | set(layer_counts.keys()))
    suggestions = suggest_layers(layer_counts)
    inferred_floor_area_sf = infer_floor_area(doc, suggestions.get("boundary", []))

    return {
        "id": uuid.uuid4().hex,
        "filename": filename,
        "layers": layers,
        "layer_counts": layer_counts,
        "suggestions": suggestions,
        "inferred_floor_area_sf": inferred_floor_area_sf,
        "require_unit_confirmation": inferred_floor_area_sf > 10_000.0,
    }


def _layer_counts(doc) -> Dict[str, Dict[str, int]]:
    counts: Dict[str, Dict[str, int]] = {}
    for entity in doc.modelspace():
        layer = getattr(entity.dxf, "layer", "0")
        counts.setdefault(layer, {})
        kind = entity.dxftype()
        counts[layer][kind] = counts[layer].get(kind, 0) + 1
    return counts


def suggest_layers(layer_counts: Dict[str, Dict[str, int]]) -> Dict[str, List[str]]:
    suggestions: Dict[str, List[str]] = {}
    layers = list(layer_counts.keys())
    for role, keywords in ROLE_KEYWORDS.items():
        ranked = sorted(
            layers,
            key=lambda layer: _score_layer(role, layer, layer_counts[layer], keywords),
            reverse=True,
        )
        positive = [
            layer
            for layer in ranked
            if _score_layer(role, layer, layer_counts[layer], keywords) > 0
        ]
        if positive:
            top_score = _score_layer(role, positive[0], layer_counts[positive[0]], keywords)
            suggestions[role] = [
                layer
                for layer in positive
                if _score_layer(role, layer, layer_counts[layer], keywords) == top_score
            ][:3]
        else:
            suggestions[role] = []
    return suggestions


def _score_layer(role: str, layer: str, counts: Dict[str, int], keywords: List[str]) -> int:
    value = layer.lower()
    score = 0
    for keyword in keywords:
        if keyword in value:
            score += 10 if keyword == value else 5

    if role == "boundary" and any(
        kind in counts for kind in {"LINE", "LWPOLYLINE", "POLYLINE", "CIRCLE", "ARC"}
    ):
        score += 3
    if role == "wall" and any(kind in counts for kind in {"LINE", "LWPOLYLINE", "POLYLINE"}):
        score += 3
    if role == "support_point":
        if counts.get("POINT", 0):
            score += 20
        if any(kind in counts for kind in {"TEXT", "MTEXT"}):
            score -= 8
    if role in {"column_label", "floor_label"} and any(
        kind in counts for kind in {"TEXT", "MTEXT"}
    ):
        score += 4
    if role == "column_label" and counts.get("POINT", 0):
        score -= 6
    if role == "floor_label" and counts.get("POINT", 0):
        score -= 6
    return score


def infer_floor_area(doc, boundary_layers: List[str]) -> float:
    if not boundary_layers:
        return 0.0

    entities = [
        entity
        for entity in doc.modelspace()
        if getattr(entity.dxf, "layer", "") in set(boundary_layers)
    ]
    loop_polygons = polygons_from_entities(entities, factor=1.0 / 12.0)
    surfaces = build_floor_surfaces(loop_polygons)
    if not surfaces:
        return 0.0

    geometry = unary_union(surfaces)
    return float(geometry.area)
