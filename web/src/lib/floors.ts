import type { FloorData } from "./types";

const RANGE_FLOOR_RE =
  /^\s*([A-Za-z]*)(\d+)\s*[-\u2013\u2014]\s*([A-Za-z]*)(\d+)\s*$/;
const UPPER_LAYOUT_FLOOR_BASE = 900_000;

export interface RenderFloorInstance {
  floor: FloorData;
  sourceFloorId: string;
  displayFloorId: string;
  instanceId: string;
  stackIndex: number;
  floorElevation: number;
  // True when this is the lowest expansion of a grouped floor (e.g.
  // "29-35" → only the "29" instance has this set to true). Used to
  // limit per-floor markers (transfer dot, etc.) to one plate per
  // logical group instead of repeating them across every stacked level.
  isBottomOfGroup: boolean;
}

export function expandFloorIdentifier(floorId: string): string[] {
  const floorText = floorId.trim();
  const match = RANGE_FLOOR_RE.exec(floorText);

  if (!match) {
    return [floorText];
  }

  const [, startPrefix, startNumber, endPrefix, endNumber] = match;
  if (startPrefix.toUpperCase() !== endPrefix.toUpperCase()) {
    return [floorText];
  }

  const start = Number.parseInt(startNumber, 10);
  const end = Number.parseInt(endNumber, 10);
  const step = end >= start ? 1 : -1;
  const prefix = startPrefix.toUpperCase();
  const floors: string[] = [];

  for (let value = start; step > 0 ? value <= end : value >= end; value += step) {
    floors.push(prefix ? `${prefix}${value}` : String(value));
  }

  return floors;
}

export function expandedPhysicalFloorCount(floors: FloorData[]): number {
  return floors.reduce(
    (total, floor) => total + expandFloorIdentifier(floor.floor_id).length,
    0,
  );
}

export function buildFloorInstances(
  floors: FloorData[],
  floorSpacingFt: number,
): RenderFloorInstance[] {
  const sourceInstances = floors.flatMap((floor) =>
    expandFloorIdentifier(floor.floor_id).map((displayFloorId, repeatIndex) => ({
      floor,
      sourceFloorId: floor.floor_id,
      displayFloorId,
      instanceId: `${floor.floor_index}:${floor.floor_id}:${displayFloorId}:${repeatIndex}`,
      stackIndex: 0,
      floorElevation: 0,
      // expandFloorIdentifier returns from start→end (low to high), so
      // index 0 is the lowest physical floor of the group.
      isBottomOfGroup: repeatIndex === 0,
    })),
  );

  return sourceInstances
    .sort((a, b) => {
      const floorDelta =
        floorStackSortValue(a.floor, a.displayFloorId) -
        floorStackSortValue(b.floor, b.displayFloorId);
      if (floorDelta !== 0) return floorDelta;

      const sourceDelta = a.floor.floor_index - b.floor.floor_index;
      if (sourceDelta !== 0) return sourceDelta;

      return a.displayFloorId.localeCompare(b.displayFloorId, undefined, {
        numeric: true,
      });
    })
    .map((instance, stackIndex) => ({
      ...instance,
      stackIndex,
      floorElevation: stackIndex * floorSpacingFt,
    }));
}

export function floorStackSortValue(
  floor: FloorData,
  floorId: string = floor.floor_id,
): number {
  const fallback = floorSortValue(floorId);
  if (!isLayoutOrderedUpperFloor(floorId)) return fallback;

  const layoutX = floorLayoutX(floor);
  if (layoutX === null) return fallback;

  return UPPER_LAYOUT_FLOOR_BASE + layoutX;
}

export function floorSortValue(floorId: string): number {
  const floorText = floorId.trim().toUpperCase();
  const compactFloorText = floorText.replace(/[^A-Z0-9]/g, "");

  if (
    compactFloorText.startsWith("EMR") ||
    floorText.includes("ELEVATOR MACHINE ROOM") ||
    floorText.includes("MACHINE ROOM")
  ) {
    const match = compactFloorText.match(/\d+/);
    return 970 + (match ? Number.parseInt(match[0], 10) : 0);
  }
  if (floorText.includes("BULKHEAD") || floorText.includes("BULK HEAD")) return 950;
  if (floorText.includes("ROOF") && floorText.includes("MAIN")) return 1000;
  if (floorText.includes("ROOF")) return 900;
  if (floorText.includes("PENTHOUSE") || floorText === "PH") return 800;
  if (floorText.startsWith("PH")) {
    const match = floorText.match(/\d+/);
    return 800 + (match ? Number.parseInt(match[0], 10) : 0);
  }
  if (
    floorText === "G" ||
    floorText === "GROUND" ||
    floorText === "MAIN" ||
    floorText.includes("LOBBY")
  ) {
    return 0;
  }

  const basementMatch =
    floorText.match(/^B\s*(\d+)/) ?? floorText.match(/^BASEMENT\s*(\d*)/);
  if (basementMatch) {
    const basementNumber = basementMatch[1]
      ? Number.parseInt(basementMatch[1], 10)
      : 1;
    return -basementNumber;
  }

  const numericMatch = floorText.match(/\d+/);
  if (numericMatch) {
    return Number.parseInt(numericMatch[0], 10);
  }

  return 0;
}

function isLayoutOrderedUpperFloor(floorId: string): boolean {
  const floorText = floorId.trim().toUpperCase();
  const compactFloorText = floorText.replace(/[^A-Z0-9]/g, "");
  return (
    floorText.includes("ROOF") ||
    floorText.includes("BULKHEAD") ||
    floorText.includes("BULK HEAD") ||
    compactFloorText.startsWith("EMR") ||
    floorText.includes("ELEVATOR MACHINE ROOM") ||
    floorText.includes("MACHINE ROOM") ||
    floorText.includes("PENTHOUSE") ||
    floorText === "PH" ||
    compactFloorText.startsWith("PH")
  );
}

function floorLayoutX(floor: FloorData): number | null {
  if (floor.alignment_datum) return floor.alignment_datum[0];

  const xs: number[] = [];
  if (floor.slab_boundary?.type === "Polygon") {
    collectPolygonXs(floor.slab_boundary.coordinates, xs);
  } else if (floor.slab_boundary?.type === "MultiPolygon") {
    for (const polygon of floor.slab_boundary.coordinates) {
      collectPolygonXs(polygon, xs);
    }
  }

  if (xs.length === 0) return null;
  return (Math.min(...xs) + Math.max(...xs)) / 2;
}

function collectPolygonXs(rings: number[][][], xs: number[]): void {
  for (const ring of rings) {
    for (const coord of ring) {
      if (Number.isFinite(coord[0])) xs.push(coord[0]);
    }
  }
}
