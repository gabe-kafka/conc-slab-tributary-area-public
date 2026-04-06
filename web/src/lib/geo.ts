import type { GeoJsonPolygon, GeoJsonMultiPolygon, GeometryBounds } from "./types";

/**
 * Convert a GeoJSON Polygon's coordinate rings to flat [x1,y1,x2,y2,...] arrays
 * that Konva's Line component expects.
 */
export function polygonToKonvaPoints(coords: number[][]): number[] {
  const flat: number[] = [];
  for (const [x, y] of coords) {
    flat.push(x, y);
  }
  return flat;
}

/**
 * Extract all polygon rings (exterior + holes) from a GeoJSON geometry.
 * Returns array of flat point arrays. First is exterior, rest are holes.
 */
export function geometryToRings(
  geom: GeoJsonPolygon | GeoJsonMultiPolygon | null,
): number[][][] {
  if (!geom) return [];

  if (geom.type === "Polygon") {
    return geom.coordinates;
  }

  if (geom.type === "MultiPolygon") {
    // Flatten all polygons' rings into a single array
    return geom.coordinates.flat();
  }

  return [];
}

/**
 * Compute the affine transform to fit geometry bounds into a canvas viewport.
 * CAD: Y-up. Canvas: Y-down. This handles the flip.
 */
export function computeViewTransform(
  bounds: GeometryBounds,
  canvasWidth: number,
  canvasHeight: number,
  padding: number = 40,
) {
  const geoWidth = bounds.max_x - bounds.min_x;
  const geoHeight = bounds.max_y - bounds.min_y;

  if (geoWidth <= 0 || geoHeight <= 0) {
    return { scaleX: 1, scaleY: -1, offsetX: 0, offsetY: 0, scale: 1 };
  }

  const availWidth = canvasWidth - padding * 2;
  const availHeight = canvasHeight - padding * 2;

  const scale = Math.min(availWidth / geoWidth, availHeight / geoHeight);

  // Center the geometry in the viewport
  const scaledWidth = geoWidth * scale;
  const scaledHeight = geoHeight * scale;
  const offsetX = (canvasWidth - scaledWidth) / 2 - bounds.min_x * scale;
  // Y-flip: canvas Y increases downward, CAD Y increases upward
  const offsetY = (canvasHeight + scaledHeight) / 2 + bounds.min_y * scale;

  return { scaleX: scale, scaleY: -scale, offsetX, offsetY, scale };
}

/**
 * Compute centroid of a coordinate ring.
 */
export function ringCentroid(coords: number[][]): [number, number] {
  if (!coords.length) return [0, 0];
  let sx = 0;
  let sy = 0;
  // Exclude the closing point if it duplicates the first
  const n =
    coords.length > 1 &&
    coords[0][0] === coords[coords.length - 1][0] &&
    coords[0][1] === coords[coords.length - 1][1]
      ? coords.length - 1
      : coords.length;
  for (let i = 0; i < n; i++) {
    sx += coords[i][0];
    sy += coords[i][1];
  }
  return [sx / n, sy / n];
}

/**
 * Generate a distinct color for a tributary region based on index.
 * Returns HSL string suitable for Konva fill.
 */
export function regionColor(index: number, total: number, alpha: number = 0.2): string {
  const hue = (index * 360) / Math.max(total, 1) + 210; // Start from blue
  return `hsla(${hue % 360}, 65%, 55%, ${alpha})`;
}

export function regionStrokeColor(index: number, total: number): string {
  const hue = (index * 360) / Math.max(total, 1) + 210;
  return `hsla(${hue % 360}, 65%, 55%, 0.6)`;
}

export const WALL_FILL = "hsla(0, 70%, 50%, 0.15)";
export const WALL_STROKE = "hsla(0, 70%, 50%, 0.5)";
export const WALL_TRIB_FILL = "hsla(0, 0%, 50%, 0.10)";
export const WALL_TRIB_STROKE = "hsla(0, 0%, 50%, 0.25)";
export const SLAB_STROKE = "#e5e5e5";
export const SELECTED_FILL = "hsla(217, 91%, 60%, 0.35)";
export const SELECTED_STROKE = "#3b82f6";
export const HOVER_ALPHA = 0.3;
export const COLUMN_POINT_COLOR = "#3b82f6";
export const COLUMN_POINT_RADIUS = 3;
