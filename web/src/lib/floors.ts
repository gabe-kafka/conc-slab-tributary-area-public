import type { FloorData } from "./types";

const RANGE_FLOOR_RE =
  /^\s*([A-Za-z]*)(\d+)\s*[-\u2013\u2014]\s*([A-Za-z]*)(\d+)\s*$/;

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
        floorSortValue(a.displayFloorId) - floorSortValue(b.displayFloorId);
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

export function floorSortValue(floorId: string): number {
  const floorText = floorId.trim().toUpperCase();

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
