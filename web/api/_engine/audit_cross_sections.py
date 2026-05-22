"""
Cross-section audit harness — runs both the OLD circularity-threshold
algorithm and the NEW shape-aware algorithm on every column footprint
in a DXF, and emits a per-footprint CSV plus a summary printout.

Usage:
    python3 audit_cross_sections.py path/to/input.dxf [COLS_layer_name]

Outputs (alongside the DXF):
    - <name>.audit.csv       per-footprint rows
    - <name>.audit.summary   printed to stdout
"""
from __future__ import annotations

import csv
import math
import sys
from collections import Counter
from pathlib import Path

import ezdxf
from shapely.geometry import Polygon

# Add this directory to path so we can import the production module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry_utils import entity_to_polygon  # noqa: E402

# --- Old algorithm (frozen copy for before/after comparison) -----------------

OLD_CIRCULARITY_THRESHOLD = 0.92


def _round_in(val_in: float) -> int:
    return int(math.floor(val_in + 0.5)) if val_in >= 0 else -int(math.floor(-val_in + 0.5))


def old_format(footprint: Polygon | None) -> str | None:
    if footprint is None or footprint.is_empty:
        return None
    area_ft2 = footprint.area
    perim_ft = footprint.length
    if area_ft2 <= 1e-9 or perim_ft <= 1e-9:
        return None
    circularity = 4.0 * math.pi * area_ft2 / (perim_ft * perim_ft)
    if circularity >= OLD_CIRCULARITY_THRESHOLD:
        diameter_in = 2.0 * math.sqrt(area_ft2 / math.pi) * 12.0
        return f"d{_round_in(diameter_in)}"
    min_rect = footprint.minimum_rotated_rectangle
    rc = list(min_rect.exterior.coords)
    if len(rc) < 5:
        return None
    sa = math.hypot(rc[1][0] - rc[0][0], rc[1][1] - rc[0][1]) * 12.0
    sb = math.hypot(rc[2][0] - rc[1][0], rc[2][1] - rc[1][1]) * 12.0
    return f"{_round_in(min(sa, sb))}x{_round_in(max(sa, sb))}"


# --- New algorithm (production import) ---------------------------------------

from export_column_loads import format_cross_section as new_format  # noqa: E402


# --- Shape classification (for the audit row) --------------------------------

SHAPE_TAG_BY_VERTEX = {3: "triangle", 5: "pentagon", 6: "hexagon"}


def classify_shape(poly: Polygon, n_vertices: int, circularity: float) -> str:
    if circularity >= 0.96:
        return "circle"
    if n_vertices == 8 and circularity >= 0.92:
        return "octagon"
    if n_vertices in SHAPE_TAG_BY_VERTEX:
        return SHAPE_TAG_BY_VERTEX[n_vertices]
    try:
        hull_area = poly.convex_hull.area
        if hull_area > 1e-9 and poly.area / hull_area < 0.85:
            return "non_convex"
    except Exception:
        pass
    # 4-vertex rectangles — rotation is irrelevant, only dims matter.
    if n_vertices == 4:
        return "rect"
    return "polygon"


# --- Per-footprint metrics ---------------------------------------------------

def collect_metrics(poly: Polygon, dxftype: str) -> dict:
    coords = list(poly.exterior.coords)
    if coords and coords[0] == coords[-1]:
        coords = coords[:-1]
    n = len(coords)
    area_in2 = poly.area * 144.0
    perim_in = poly.length * 12.0
    circularity = (
        4.0 * math.pi * poly.area / (poly.length * poly.length)
        if poly.length > 1e-9 else 0.0
    )

    # bbox
    minx, miny, maxx, maxy = poly.bounds
    bbox_w = (maxx - minx) * 12.0
    bbox_h = (maxy - miny) * 12.0

    # mrr
    mrr = poly.minimum_rotated_rectangle
    rc = list(mrr.exterior.coords)
    mrr_w = mrr_h = 0.0
    if len(rc) >= 5:
        sa = math.hypot(rc[1][0] - rc[0][0], rc[1][1] - rc[0][1]) * 12.0
        sb = math.hypot(rc[2][0] - rc[1][0], rc[2][1] - rc[1][1]) * 12.0
        mrr_w = min(sa, sb)
        mrr_h = max(sa, sb)

    try:
        hull_area = poly.convex_hull.area
        convex_fill = poly.area / hull_area if hull_area > 1e-9 else 1.0
    except Exception:
        convex_fill = 1.0
    is_convex = convex_fill >= 0.999

    shape_class = classify_shape(poly, n, circularity)

    # Anomaly notes — flag drafted-looking issues for human review.
    anomalies = []
    if not is_convex:
        anomalies.append(f"non_convex({convex_fill:.2f})")
    if n in (3, 5, 6):
        anomalies.append(f"n={n}")
    if n == 8 and 0.92 <= circularity < 0.96:
        anomalies.append("octagon_band")

    return {
        "dxftype": dxftype,
        "n_vertices": n,
        "is_convex": is_convex,
        "convex_fill": round(convex_fill, 3),
        "area_in2": round(area_in2, 2),
        "perim_in": round(perim_in, 2),
        "circularity": round(circularity, 4),
        "bbox_w_in": round(bbox_w, 2),
        "bbox_h_in": round(bbox_h, 2),
        "mrr_w_in": round(mrr_w, 2),
        "mrr_h_in": round(mrr_h, 2),
        "shape_class": shape_class,
        "anomalies": ",".join(anomalies),
    }


# --- Main --------------------------------------------------------------------

def run_audit(dxf_path: Path, layer: str = "COLS") -> dict:
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    factor = 1.0 / 12.0  # assume inches → feet (matches demo)

    rows = []
    for entity in msp:
        if getattr(entity.dxf, "layer", "") != layer:
            continue
        poly = entity_to_polygon(entity, factor)
        if poly is None or poly.is_empty or poly.area < 0.25:
            continue
        m = collect_metrics(poly, entity.dxftype())
        m["handle"] = entity.dxf.handle
        m["layer"] = layer
        m["current_label"] = old_format(poly)
        m["proposed_label"] = new_format(poly)
        m["changed"] = m["current_label"] != m["proposed_label"]
        rows.append(m)

    # Write CSV.
    out_csv = dxf_path.with_suffix(".audit.csv")
    fields = [
        "handle", "layer", "dxftype", "shape_class", "n_vertices", "is_convex",
        "convex_fill", "area_in2", "perim_in", "circularity",
        "bbox_w_in", "bbox_h_in", "mrr_w_in", "mrr_h_in",
        "current_label", "proposed_label", "changed", "anomalies",
    ]
    with out_csv.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Summaries.
    by_shape = Counter(r["shape_class"] for r in rows)
    changes = [r for r in rows if r["changed"]]
    change_pairs = Counter((r["current_label"], r["proposed_label"]) for r in changes)

    summary = {
        "csv": str(out_csv),
        "total_footprints": len(rows),
        "by_shape": dict(by_shape),
        "n_changed": len(changes),
        "change_pairs": [
            {"current": c, "proposed": p, "count": n}
            for (c, p), n in change_pairs.most_common()
        ],
        "anomaly_counts": dict(Counter(
            a for r in rows for a in (r["anomalies"].split(",") if r["anomalies"] else [])
        )),
    }
    return summary


def _print_summary(s: dict) -> None:
    print("=" * 70)
    print("CROSS-SECTION AUDIT")
    print("=" * 70)
    print(f"Total footprints: {s['total_footprints']}")
    print(f"CSV: {s['csv']}\n")
    print("Shape class distribution:")
    for k, v in sorted(s["by_shape"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:<15} {v}")
    print(f"\nLabels changed by new algorithm: {s['n_changed']}")
    if s["change_pairs"]:
        print("\nLabel changes (current → proposed × count):")
        for cp in s["change_pairs"][:30]:
            print(f"  {cp['current']!r:<14} → {cp['proposed']!r:<14}  × {cp['count']}")
    if s["anomaly_counts"]:
        print("\nAnomalies flagged:")
        for k, v in sorted(s["anomaly_counts"].items(), key=lambda kv: -kv[1]):
            print(f"  {k:<24} {v}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: audit_cross_sections.py path/to/input.dxf [LAYER]")
        sys.exit(2)
    dxf_path = Path(sys.argv[1]).resolve()
    layer = sys.argv[2] if len(sys.argv) > 2 else "COLS"
    summary = run_audit(dxf_path, layer)
    _print_summary(summary)
