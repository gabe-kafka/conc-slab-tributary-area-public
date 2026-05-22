"""AI-assisted selection of per-floor alignment datums.

Given each floor's wall geometry, asks the model to identify an inside
corner of an elevator (or stair) core — these run vertically through
the building and stay in the same relative position on every floor,
making them the most reliable alignment anchor.

Returns a {floor_id: (x, y)} mapping. Empty dict on any failure;
caller should fall back to wall-centroid alignment.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Dict, List, Tuple


_AI_DATUM_MODEL_ENV = "OPENAI_DATUM_MODEL"
_AI_DATUM_MODEL_DEFAULT = "gpt-5.4-mini"
_MAX_VERTICES_PER_WALL = 16


def select_alignment_datums(floor_plans) -> Dict[str, Tuple[float, float]]:
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return {}

    floors_payload: Dict[str, List[List[List[float]]]] = {}
    for fp in floor_plans:
        floor_id = str(fp.get("floor_number", fp.get("boundary_id", "UNKNOWN")))
        wall_coords: List[List[List[float]]] = []
        for w in fp.get("walls") or []:
            line = w.get("wall_line")
            if line is None or line.is_empty:
                continue
            coords = list(line.coords)[:_MAX_VERTICES_PER_WALL]
            wall_coords.append([[round(x, 1), round(y, 1)] for x, y in coords])
        if wall_coords:
            floors_payload[floor_id] = wall_coords

    if len(floors_payload) < 2:
        return {}

    model = os.environ.get(_AI_DATUM_MODEL_ENV, _AI_DATUM_MODEL_DEFAULT)
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "You align multi-story floor plans of one building. Each "
                    "floor's walls live in the same DXF coordinate system but "
                    "each floor's drawing sits in its own (x,y) region of "
                    "model space. Pick ONE point per floor that corresponds "
                    "to the SAME physical feature on every floor — preferably "
                    "an INSIDE CORNER of an elevator shaft (most stable). "
                    "Stair-core inside corner is the next-best option. The "
                    "point must lie on (or within ~6 inches of) an actual "
                    "wall vertex you were given for that floor. Datums "
                    "across floors must reference the same elevator/stair "
                    "corner — use the relative geometry of walls to find the "
                    "match on each floor. Return only the requested JSON."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"floors": floors_payload}, separators=(",", ":")),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "datum_per_floor",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["datum_description", "datums"],
                    "properties": {
                        "datum_description": {"type": "string"},
                        "datums": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                        },
                    },
                },
            }
        },
        "max_output_tokens": 1500,
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:500]
        print(f"WARNING: AI datum selection HTTP {exc.code}: {detail}")
        return {}
    except Exception as exc:
        print(f"WARNING: AI datum selection failed: {exc}")
        return {}

    text = _extract_response_text(body)
    if not text:
        print("WARNING: AI datum response had no text output")
        return {}

    try:
        parsed = json.loads(text)
    except Exception as exc:
        print(f"WARNING: AI datum response unparseable: {exc}")
        return {}

    description = parsed.get("datum_description", "?")
    datums_raw = parsed.get("datums", {})
    datums: Dict[str, Tuple[float, float]] = {}
    for fid, xy in datums_raw.items():
        if isinstance(xy, list) and len(xy) == 2:
            try:
                datums[str(fid)] = (float(xy[0]), float(xy[1]))
            except (TypeError, ValueError):
                continue

    if datums:
        print(f"AI alignment datum: {description} ({len(datums)} floors)")
    return datums


def _extract_response_text(body: dict) -> str:
    for item in body.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text":
                return content.get("text", "") or ""
    return ""
