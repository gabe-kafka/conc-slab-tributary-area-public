#!/usr/bin/env python3
"""Generate an animated GIF showing tributary area computation.

Reads geometry.json (produced by the tributary pipeline) and creates
a dark-themed animation of one floor's tributary regions being built
step-by-step: boundary draw-in, column placement, Voronoi construction,
clipping, and region fill.

Usage:
    python scripts/generate_tributary_gif.py --input geometry.json --output tributary.gif
"""

import argparse
import colorsys
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import numpy as np
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.animation import FuncAnimation, PillowWriter
from shapely.geometry import (
    MultiPoint, MultiPolygon, Polygon, LineString, shape,
)
from shapely.ops import voronoi_diagram

# ---------------------------------------------------------------------------
# Theme (matches web/src/app/globals.css + web/src/lib/geo.ts)
# ---------------------------------------------------------------------------
BG_BASE = "#0a0a0a"
BG_SURFACE = "#141414"
SLAB_STROKE = "#e5e5e5"
ACCENT = "#3b82f6"
TEXT_PRIMARY = "#e5e5e5"
TEXT_SECONDARY = "#a0a0a0"
TEXT_MUTED = "#666666"
WALL_LINE_COLOR = "#ef4444"      # red — matches geo.ts WALL_STROKE
WALL_TRIB_FILL = (0.5, 0.5, 0.5, 0.10)   # gray 10% — matches WALL_TRIB_FILL
WALL_TRIB_STROKE = (0.5, 0.5, 0.5, 0.25)  # gray 25% — matches WALL_TRIB_STROKE

# Canvas — render at 2x for sharp output, then Pillow downscales in the GIF
WIDTH_PX, HEIGHT_PX = 2400, 1254
DPI = 200
FIG_W = WIDTH_PX / DPI
FIG_H = HEIGHT_PX / DPI

# Animation timing (frames)
FPS = 20
PHASE_BOUNDARY = (0, 34)       # 1.75s  - slab perimeter traces in
PHASE_COLUMNS = (35, 59)       # 1.25s  - column points appear
PHASE_VORONOI = (60, 99)       # 2.0s   - raw Voronoi edges draw
PHASE_CLIP = (100, 119)        # 1.0s   - exterior fades, interior solidifies
PHASE_FILL = (120, 154)        # 1.75s  - regions fill with color
PHASE_HOLD = (155, 179)        # 1.25s  - final frame hold
TOTAL_FRAMES = 180

# Voronoi
VORONOI_PADDING = 20.0  # feet beyond slab for raw diagram


# ---------------------------------------------------------------------------
# Color helpers (replicates geo.ts regionColor exactly)
# ---------------------------------------------------------------------------

def region_color_rgba(index: int, total: int, alpha: float = 0.2):
    """HSL color matching geo.ts: hue = (index*360/total) + 210."""
    hue_deg = ((index * 360) / max(total, 1) + 210) % 360
    h = hue_deg / 360.0
    s = 0.65
    l = 0.55
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (r, g, b, alpha)


def hex_to_rgba(hex_color: str, alpha: float = 1.0):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return (r, g, b, alpha)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_floor(geometry_path: str, floor_id: str | None = None):
    """Load geometry.json and return the best floor for animation."""
    with open(geometry_path) as f:
        data = json.load(f)

    floors = data["floors"]
    if floor_id:
        floor = next((f for f in floors if f["floor_id"] == floor_id), None)
        if not floor:
            print(f"Floor '{floor_id}' not found. Available: {[f['floor_id'] for f in floors]}")
            sys.exit(1)
    else:
        # Pick floor with most columns (most visually interesting)
        floor = max(floors, key=lambda f: len(f["columns"]))

    # Parse geometries
    slab_poly = shape(floor["slab_boundary"])
    columns = []
    for col in floor["columns"]:
        region = shape(col["tributary_region"])
        columns.append({
            "index": col["index"],
            "label": col["label"],
            "point": col["point"],
            "region": region,
            "area_sf": col["area_sf"],
        })

    walls = []
    for w in floor.get("walls", []):
        walls.append({
            "wall_index": w["wall_index"],
            "wall_line": shape(w["wall_line"]),
            "region": shape(w["tributary_region"]),
            "area_sf": w["area_sf"],
        })

    # Floor-local bounds
    bounds = slab_poly.bounds  # (minx, miny, maxx, maxy)
    return slab_poly, columns, walls, bounds, floor["floor_id"]


# ---------------------------------------------------------------------------
# Voronoi edge extraction
# ---------------------------------------------------------------------------

def compute_voronoi_edges(columns, slab_poly):
    """Compute raw (unclipped) Voronoi edges extending beyond the slab."""
    points = [c["point"] for c in columns]
    mp = MultiPoint(points)
    envelope = slab_poly.envelope.buffer(VORONOI_PADDING)

    diagram = voronoi_diagram(mp, envelope=envelope, edges=False)
    cells = list(getattr(diagram, "geoms", [diagram]))

    # Extract edges as line segments from cell boundaries
    all_edges = []
    interior_edges = []
    exterior_edges = []

    # Get all unique edges by intersecting adjacent cell boundaries
    for i, cell in enumerate(cells):
        if cell.is_empty:
            continue
        boundary = cell.boundary
        # Clip to a reasonable viewing area
        view_box = slab_poly.envelope.buffer(VORONOI_PADDING * 0.6)
        clipped_boundary = boundary.intersection(view_box)
        if clipped_boundary.is_empty:
            continue

        # Split into segments
        if hasattr(clipped_boundary, "geoms"):
            for geom in clipped_boundary.geoms:
                if geom.geom_type == "LineString":
                    coords = list(geom.coords)
                    for j in range(len(coords) - 1):
                        seg = (coords[j], coords[j + 1])
                        all_edges.append(seg)
        elif clipped_boundary.geom_type == "LineString":
            coords = list(clipped_boundary.coords)
            for j in range(len(coords) - 1):
                seg = (coords[j], coords[j + 1])
                all_edges.append(seg)

    # Deduplicate edges (within tolerance)
    seen = set()
    unique_edges = []
    for seg in all_edges:
        key = (round(seg[0][0], 2), round(seg[0][1], 2),
               round(seg[1][0], 2), round(seg[1][1], 2))
        rev_key = (key[2], key[3], key[0], key[1])
        if key not in seen and rev_key not in seen:
            seen.add(key)
            line = LineString(seg)
            is_interior = slab_poly.contains(line) or slab_poly.boundary.distance(line) < 0.5
            unique_edges.append((seg, is_interior))

    return unique_edges


def interpolate_ring(coords, fraction):
    """Return the first `fraction` of a coordinate ring as a list of points."""
    if fraction >= 1.0:
        return coords
    if fraction <= 0.0:
        return []

    # Compute cumulative distances
    dists = [0.0]
    for i in range(1, len(coords)):
        dx = coords[i][0] - coords[i - 1][0]
        dy = coords[i][1] - coords[i - 1][1]
        dists.append(dists[-1] + (dx * dx + dy * dy) ** 0.5)

    total = dists[-1]
    if total == 0:
        return [coords[0]]

    target = total * fraction
    result = [coords[0]]
    for i in range(1, len(coords)):
        if dists[i] <= target:
            result.append(coords[i])
        else:
            # Interpolate between i-1 and i
            remaining = target - dists[i - 1]
            seg_len = dists[i] - dists[i - 1]
            if seg_len > 0:
                t = remaining / seg_len
                x = coords[i - 1][0] + t * (coords[i][0] - coords[i - 1][0])
                y = coords[i - 1][1] + t * (coords[i][1] - coords[i - 1][1])
                result.append((x, y))
            break

    return result


def ease_out_cubic(t):
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_quad(t):
    if t < 0.5:
        return 2 * t * t
    return 1 - (-2 * t + 2) ** 2 / 2


# ---------------------------------------------------------------------------
# Polygon rendering helper
# ---------------------------------------------------------------------------

def shapely_to_patches(geom):
    """Convert a Shapely polygon/multipolygon to matplotlib Polygon patches."""
    patches = []
    if geom.geom_type == "Polygon":
        ext = list(geom.exterior.coords)
        holes = [list(h.coords) for h in geom.interiors]
        patches.append(mpatches.Polygon(ext, closed=True))
    elif geom.geom_type == "MultiPolygon":
        for poly in geom.geoms:
            ext = list(poly.exterior.coords)
            patches.append(mpatches.Polygon(ext, closed=True))
    return patches


# ---------------------------------------------------------------------------
# Main animation
# ---------------------------------------------------------------------------

def generate_gif(geometry_path: str, output_path: str, floor_id: str | None = None):
    slab_poly, columns, walls, bounds, fid = load_floor(geometry_path, floor_id)
    total_cols = len(columns)
    print(f"Floor '{fid}': {total_cols} columns, {len(walls)} walls, slab area {slab_poly.area:.0f} SF")

    # Sort columns by spatial position (left-to-right, bottom-to-top) for visual order
    columns.sort(key=lambda c: (c["point"][0], c["point"][1]))

    # Pre-compute Voronoi edges
    print("Computing Voronoi edges...")
    voronoi_edges = compute_voronoi_edges(columns, slab_poly)
    print(f"  {len(voronoi_edges)} unique edges")

    # Slab boundary coords
    slab_exterior = list(slab_poly.exterior.coords)

    # Setup figure — reserve top 12% for title, bottom 8% for phase label
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG_BASE)
    ax = fig.add_axes([0.02, 0.08, 0.96, 0.78])  # [left, bottom, width, height]
    ax.set_facecolor(BG_BASE)
    ax.set_aspect("equal")
    ax.axis("off")

    # Set view bounds with padding
    minx, miny, maxx, maxy = bounds
    pad_x = (maxx - minx) * 0.10
    pad_y = (maxy - miny) * 0.10
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)

    # Try to use Menlo font
    mono_font = "monospace"
    for font_path in ["/System/Library/Fonts/Menlo.ttc",
                      "/System/Library/Fonts/SFMono-Regular.otf"]:
        if Path(font_path).exists():
            try:
                fm.fontManager.addfont(font_path)
                prop = fm.FontProperties(fname=font_path)
                mono_font = prop.get_name()
                break
            except Exception:
                pass

    font_props = {"family": mono_font, "size": 8}
    font_props_small = {"family": mono_font, "size": 6}
    font_props_title = {"family": mono_font, "size": 14, "weight": "bold"}
    font_props_subtitle = {"family": mono_font, "size": 8}

    def draw_frame(frame):
        # Clear axes and any previous fig-level texts
        ax.clear()
        for txt in list(fig.texts):
            txt.remove()
        ax.set_facecolor(BG_BASE)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(minx - pad_x, maxx + pad_x)
        ax.set_ylim(miny - pad_y, maxy + pad_y)

        # ---- Phase 1: Boundary draw-in ----
        p1_start, p1_end = PHASE_BOUNDARY
        if frame >= p1_start:
            if frame <= p1_end:
                t = (frame - p1_start) / (p1_end - p1_start)
                t = ease_out_cubic(t)
                partial = interpolate_ring(slab_exterior, t)
                if len(partial) >= 2:
                    xs, ys = zip(*partial)
                    ax.plot(xs, ys, color=SLAB_STROKE, linewidth=1.8, solid_capstyle="round")
            else:
                # Full boundary
                xs, ys = zip(*slab_exterior)
                ax.plot(xs, ys, color=SLAB_STROKE, linewidth=1.8, solid_capstyle="round")

                # Also draw holes if any
                for interior in slab_poly.interiors:
                    hx, hy = zip(*interior.coords)
                    ax.plot(hx, hy, color=SLAB_STROKE, linewidth=1.2, solid_capstyle="round")

                # Wall outlines (appear with boundary) — close the polyline
                # to form filled wall footprints
                for wall in walls:
                    wcoords = list(wall["wall_line"].coords)
                    # Close the polygon if not already closed
                    if wcoords[0] != wcoords[-1]:
                        wcoords.append(wcoords[0])
                    wall_patch = mpatches.Polygon(wcoords, closed=True)
                    wall_patch.set_facecolor((*hex_to_rgba(WALL_LINE_COLOR)[:3], 0.15))
                    wall_patch.set_edgecolor((*hex_to_rgba(WALL_LINE_COLOR)[:3], 0.7))
                    wall_patch.set_linewidth(1.2)
                    ax.add_patch(wall_patch)

        # ---- Phase 2: Column drop-in ----
        p2_start, p2_end = PHASE_COLUMNS
        if frame >= p2_start:
            if frame <= p2_end:
                t = (frame - p2_start) / (p2_end - p2_start)
                n_visible = max(1, int(t * total_cols) + 1)
                n_visible = min(n_visible, total_cols)
            else:
                n_visible = total_cols

            for i in range(n_visible):
                col = columns[i]
                px, py = col["point"]
                # Glow
                glow = plt.Circle((px, py), 1.8, color=ACCENT, alpha=0.15)
                ax.add_patch(glow)
                # Point
                dot = plt.Circle((px, py), 0.6, color=ACCENT, alpha=0.95)
                ax.add_patch(dot)

                # Label (only after all columns are placed)
                if frame > p2_end:
                    ax.text(px + 1.0, py + 1.0, col["label"],
                            color=TEXT_MUTED, fontsize=5, fontfamily=mono_font,
                            alpha=0.6)

        # ---- Phase 3: Voronoi construction lines ----
        p3_start, p3_end = PHASE_VORONOI
        if p3_start <= frame <= p3_end:
            t = (frame - p3_start) / (p3_end - p3_start)
            t = ease_out_cubic(t)
            n_edges = max(1, int(t * len(voronoi_edges)))

            segments = []
            colors = []
            for i in range(min(n_edges, len(voronoi_edges))):
                seg, is_interior = voronoi_edges[i]
                segments.append(seg)
                if is_interior:
                    colors.append((*hex_to_rgba(ACCENT)[:3], 0.35))
                else:
                    colors.append((*hex_to_rgba(ACCENT)[:3], 0.15))

            if segments:
                lc = LineCollection(segments, colors=colors, linewidths=0.8,
                                    linestyles="dashed")
                ax.add_collection(lc)

        # ---- Phase 4: Clip to boundary ----
        p4_start, p4_end = PHASE_CLIP
        if p4_start <= frame <= p4_end:
            t = (frame - p4_start) / (p4_end - p4_start)
            t = ease_in_out_quad(t)

            interior_segs = []
            interior_colors = []
            exterior_segs = []
            exterior_colors = []

            for seg, is_interior in voronoi_edges:
                if is_interior:
                    alpha = 0.35 + t * 0.35  # 0.35 -> 0.70
                    interior_segs.append(seg)
                    interior_colors.append((*hex_to_rgba(ACCENT)[:3], alpha))
                else:
                    alpha = 0.15 * (1.0 - t)  # 0.15 -> 0
                    exterior_segs.append(seg)
                    exterior_colors.append((*hex_to_rgba(ACCENT)[:3], alpha))

            if exterior_segs:
                lc_ext = LineCollection(exterior_segs, colors=exterior_colors,
                                        linewidths=0.8, linestyles="dashed")
                ax.add_collection(lc_ext)
            if interior_segs:
                lw = 0.8 + t * 0.6  # thicken as they solidify
                ls = "dashed" if t < 0.5 else "solid"
                lc_int = LineCollection(interior_segs, colors=interior_colors,
                                        linewidths=lw, linestyles=ls)
                ax.add_collection(lc_int)

        # ---- Phase 5: Region fill ----
        p5_start, p5_end = PHASE_FILL
        if frame >= p5_start:
            if frame <= p5_end:
                t = (frame - p5_start) / (p5_end - p5_start)
                n_filled = max(1, int(t * total_cols) + 1)
                n_filled = min(n_filled, total_cols)
            else:
                n_filled = total_cols

            for i in range(n_filled):
                col = columns[i]
                fill_color = region_color_rgba(i, total_cols, alpha=0.25)
                stroke_color = region_color_rgba(i, total_cols, alpha=0.6)

                patches = shapely_to_patches(col["region"])
                for patch in patches:
                    patch.set_facecolor(fill_color)
                    patch.set_edgecolor(stroke_color)
                    patch.set_linewidth(1.0)
                    ax.add_patch(patch)

                # Area label in region centroid
                if frame > p5_start + 5:
                    centroid = col["region"].centroid
                    ax.text(centroid.x, centroid.y,
                            f"{col['area_sf']:.0f}",
                            color=TEXT_PRIMARY, fontsize=5.5, fontfamily=mono_font,
                            ha="center", va="center", alpha=0.7)

            # Wall tributary regions (fill after ~40% of column regions are done)
            wall_threshold = max(int(total_cols * 0.4), 1)
            if n_filled >= wall_threshold:
                for wall in walls:
                    w_patches = shapely_to_patches(wall["region"])
                    for wp in w_patches:
                        wp.set_facecolor(WALL_TRIB_FILL)
                        wp.set_edgecolor(WALL_TRIB_STROKE)
                        wp.set_linewidth(0.8)
                        ax.add_patch(wp)

                    # Wall area label
                    if frame > p5_start + 10:
                        wc = wall["region"].centroid
                        ax.text(wc.x, wc.y, f"{wall['area_sf']:.0f}",
                                color=TEXT_SECONDARY, fontsize=4.5, fontfamily=mono_font,
                                ha="center", va="center", alpha=0.5)

                # Re-draw wall outlines on top of tributary fills
                for wall in walls:
                    wcoords = list(wall["wall_line"].coords)
                    if wcoords[0] != wcoords[-1]:
                        wcoords.append(wcoords[0])
                    wall_patch = mpatches.Polygon(wcoords, closed=True)
                    wall_patch.set_facecolor((*hex_to_rgba(WALL_LINE_COLOR)[:3], 0.15))
                    wall_patch.set_edgecolor((*hex_to_rgba(WALL_LINE_COLOR)[:3], 0.7))
                    wall_patch.set_linewidth(1.2)
                    ax.add_patch(wall_patch)

            # Re-draw Voronoi interior edges as solid (behind regions they're covered,
            # but visible at region borders)
            interior_segs = [seg for seg, is_int in voronoi_edges if is_int]
            if interior_segs:
                lc = LineCollection(interior_segs,
                                    colors=[(*hex_to_rgba(ACCENT)[:3], 0.25)] * len(interior_segs),
                                    linewidths=0.5, linestyles="solid")
                ax.add_collection(lc)

        # ---- Phase 6: Hold with title ----
        p6_start, p6_end = PHASE_HOLD
        if frame >= p6_start:
            # Title — in figure space, above the axes
            fig.text(0.5, 0.94, "TRIBUTARY PLATE SLAB",
                     color=ACCENT, ha="center", va="top", **font_props_title)
            # Subtitle
            fig.text(0.5, 0.89, "Automated Tributary Area Computation",
                     color=TEXT_SECONDARY, ha="center", va="top", **font_props_subtitle)
            # Floor info — bottom right, figure space
            fig.text(0.97, 0.02, f"Floor {fid}  |  {total_cols} columns",
                     color=TEXT_MUTED, ha="right", va="bottom",
                     fontsize=6, fontfamily=mono_font)

        # ---- Persistent phase label — bottom left, figure space ----
        if frame < p2_start:
            phase_label = "SLAB BOUNDARY"
        elif frame < p3_start:
            phase_label = f"COLUMN SUPPORTS: {total_cols}"
        elif frame < p4_start:
            phase_label = "VORONOI TESSELLATION"
        elif frame < p5_start:
            phase_label = "CLIPPING TO BOUNDARY"
        elif frame < p6_start:
            phase_label = "TRIBUTARY AREAS"
        else:
            phase_label = None

        if phase_label:
            fig.text(0.03, 0.02, phase_label,
                     color=TEXT_MUTED, ha="left", va="bottom",
                     fontsize=6, fontfamily=mono_font, alpha=0.6)

    # Build animation
    print(f"Rendering {TOTAL_FRAMES} frames at {FPS} fps...")
    anim = FuncAnimation(fig, draw_frame, frames=TOTAL_FRAMES, interval=1000 // FPS)

    # Save GIF
    writer = PillowWriter(fps=FPS)
    anim.save(output_path, writer=writer, dpi=DPI)
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"Saved: {output_path} ({size_mb:.1f} MB)")

    # Save MP4 if requested or alongside GIF
    mp4_path = Path(output_path).with_suffix(".mp4")
    from matplotlib.animation import FFMpegWriter
    mp4_writer = FFMpegWriter(fps=FPS, bitrate=2000,
                               extra_args=["-pix_fmt", "yuv420p"])
    anim.save(str(mp4_path), writer=mp4_writer, dpi=DPI)
    mp4_size = mp4_path.stat().st_size / (1024 * 1024)
    print(f"Saved: {mp4_path} ({mp4_size:.1f} MB)")

    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate tributary area animation GIF")
    parser.add_argument("--input", "-i", required=True, help="Path to geometry.json")
    parser.add_argument("--output", "-o", default="tributary_animation.gif", help="Output GIF path")
    parser.add_argument("--floor", "-f", default=None, help="Floor ID to animate (default: most columns)")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: {args.input} not found. Run the tributary pipeline first.")
        sys.exit(1)

    generate_gif(args.input, args.output, args.floor)


if __name__ == "__main__":
    main()
