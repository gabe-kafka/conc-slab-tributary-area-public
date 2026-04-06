"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Stage, Layer, Line, Circle, Text } from "react-konva";
import type Konva from "konva";
import type { FloorData, GeometryBounds, ColumnData, WallData } from "@/lib/types";
import {
  computeViewTransform,
  geometryToRings,
  regionColor,
  regionStrokeColor,
  ringCentroid,
  SLAB_STROKE,
  SELECTED_FILL,
  SELECTED_STROKE,
  COLUMN_POINT_COLOR,
  COLUMN_POINT_RADIUS,
} from "@/lib/geo";

interface TributaryCanvasProps {
  floors: FloorData[];
  bounds: GeometryBounds;
  visibleFloors: Set<string>;
  selectedColumn: { floorId: string; colIndex: number } | null;
  hoveredColumn: { floorId: string; colIndex: number } | null;
  onSelectColumn: (floorId: string, colIndex: number) => void;
  onHoverColumn: (floorId: string | null, colIndex: number | null) => void;
  onSelectWall: (floorId: string, wallIndex: number) => void;
}

export default function TributaryCanvas({
  floors,
  bounds,
  visibleFloors,
  selectedColumn,
  hoveredColumn,
  onSelectColumn,
  onHoverColumn,
  onSelectWall,
}: TributaryCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [stageScale, setStageScale] = useState(1);

  // Fit container
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        setSize({ width, height });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const transform = computeViewTransform(bounds, size.width, size.height);

  // Trackpad: pinch-to-zoom (ctrlKey) + two-finger pan; mouse: scroll = zoom
  const handleWheel = useCallback((e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    const stage = stageRef.current;
    if (!stage) return;

    if (e.evt.ctrlKey || e.evt.metaKey) {
      // Pinch-to-zoom (trackpad) or ctrl+scroll (mouse)
      const oldScale = stage.scaleX();
      const pointer = stage.getPointerPosition();
      if (!pointer) return;

      const zoom = 1 - e.evt.deltaY * 0.01;
      const newScale = Math.max(0.05, Math.min(oldScale * zoom, 100));

      const mousePointTo = {
        x: (pointer.x - stage.x()) / oldScale,
        y: (pointer.y - stage.y()) / oldScale,
      };

      stage.scale({ x: newScale, y: newScale });
      stage.position({
        x: pointer.x - mousePointTo.x * newScale,
        y: pointer.y - mousePointTo.y * newScale,
      });
      setStageScale(newScale);
    } else {
      // Two-finger scroll = pan
      stage.position({
        x: stage.x() - e.evt.deltaX,
        y: stage.y() - e.evt.deltaY,
      });
    }
    stage.batchDraw();
  }, []);

  return (
    <div ref={containerRef} className="flex-1 bg-bg-base overflow-hidden">
      <Stage
        ref={stageRef}
        width={size.width}
        height={size.height}
        onWheel={handleWheel}
      >
        {floors.map((floor) => {
          if (!visibleFloors.has(floor.floor_id)) return null;
          const totalCols = floor.columns.length;
          // Inverse scale factor — keeps labels/dots at constant screen size
          const inv = 1 / stageScale;
          // Label visibility: hide when too zoomed out to be readable
          const showLabels = stageScale > 0.4;
          const showDetail = stageScale > 1.5;

          return (
            <Layer key={floor.floor_id}>
              {/* Slab boundary */}
              {floor.slab_boundary &&
                geometryToRings(floor.slab_boundary).map((ring, i) => (
                  <Line
                    key={`boundary-${i}`}
                    points={transformRing(ring, transform)}
                    closed
                    stroke={SLAB_STROKE}
                    strokeWidth={1.5 * inv}
                    listening={false}
                  />
                ))}

              {/* Wall tributary regions — hidden; wall lines show location,
                  column regions fill the slab. Area data still in exports. */}

              {/* Column tributary regions */}
              {floor.columns.map((col) => {
                if (!col.tributary_region) return null;
                const isSelected =
                  selectedColumn?.floorId === floor.floor_id &&
                  selectedColumn?.colIndex === col.index;
                const isHovered =
                  hoveredColumn?.floorId === floor.floor_id &&
                  hoveredColumn?.colIndex === col.index;
                const rings = geometryToRings(col.tributary_region);
                const fill = isSelected
                  ? SELECTED_FILL
                  : regionColor(
                      col.index,
                      totalCols,
                      isHovered ? 0.3 : 0.2,
                    );
                const stroke = isSelected
                  ? SELECTED_STROKE
                  : regionStrokeColor(col.index, totalCols);

                return rings.map((ring, i) => (
                  <Line
                    key={`col-${col.index}-${i}`}
                    points={transformRing(ring, transform)}
                    closed
                    fill={i === 0 ? fill : undefined}
                    stroke={stroke}
                    strokeWidth={(isSelected ? 1.5 : 0.5) * inv}
                    onClick={() =>
                      onSelectColumn(floor.floor_id, col.index)
                    }
                    onMouseEnter={() =>
                      onHoverColumn(floor.floor_id, col.index)
                    }
                    onMouseLeave={() => onHoverColumn(null, null)}
                  />
                ));
              })}

              {/* Column point markers — constant screen size */}
              {floor.columns.map((col) => {
                const [cx, cy] = transformPoint(
                  col.point[0],
                  col.point[1],
                  transform,
                );
                return (
                  <Circle
                    key={`pt-${col.index}`}
                    x={cx}
                    y={cy}
                    radius={COLUMN_POINT_RADIUS * inv}
                    fill={COLUMN_POINT_COLOR}
                    listening={false}
                  />
                );
              })}

              {/* Column labels — anchored to column point, offset right */}
              {showLabels &&
                floor.columns.map((col) => {
                  if (col.area_sf_ceil === 0) return null;
                  const [px, py] = transformPoint(
                    col.point[0],
                    col.point[1],
                    transform,
                  );
                  const label = showDetail
                    ? `${col.label}\n${col.area_sf_ceil} SF`
                    : col.label || `${col.area_sf_ceil}`;
                  return (
                    <Text
                      key={`label-${col.index}`}
                      x={px + 6 * inv}
                      y={py - (showDetail ? 6 : 4) * inv}
                      text={label}
                      fontSize={9 * inv}
                      fontFamily="JetBrains Mono, monospace"
                      fill="#e5e5e5"
                      listening={false}
                    />
                  );
                })}

              {/* Wall linework — closed shapes for polylines, open for simple lines */}
              {floor.walls.map((wall) => {
                if (!wall.wall_line) return null;
                const coords = wall.wall_line.coordinates;
                const isClosed = coords.length >= 4;
                return (
                  <Line
                    key={`wallline-${wall.wall_index}`}
                    points={transformRing(coords, transform)}
                    closed={isClosed}
                    fill={isClosed ? "hsla(0, 70%, 45%, 0.35)" : undefined}
                    stroke="#ef4444"
                    strokeWidth={(isClosed ? 1.5 : 3) * inv}
                    lineCap="square"
                    listening={false}
                  />
                );
              })}

              {/* Floor ID label — anchored to slab boundary centroid */}
              {floor.slab_boundary && (() => {
                const rings = geometryToRings(floor.slab_boundary);
                if (!rings.length || !rings[0].length) return null;
                const [cx, cy] = ringCentroid(rings[0]);
                const [tx, ty] = transformPoint(cx, cy, transform);
                return (
                  <Text
                    key={`floor-label-${floor.floor_id}`}
                    x={tx}
                    y={ty}
                    text={floor.floor_id}
                    fontSize={16 * inv}
                    fontFamily="JetBrains Mono, monospace"
                    fontStyle="bold"
                    fill="#3b82f6"
                    opacity={0.5}
                    align="center"
                    offsetX={40 * inv}
                    offsetY={8 * inv}
                    listening={false}
                  />
                );
              })()}
            </Layer>
          );
        })}
      </Stage>
    </div>
  );
}

type Transform = ReturnType<typeof computeViewTransform>;

function transformPoint(
  x: number,
  y: number,
  t: Transform,
): [number, number] {
  return [x * t.scaleX + t.offsetX, y * t.scaleY + t.offsetY];
}

function transformRing(ring: number[][], t: Transform): number[] {
  const flat: number[] = [];
  for (const [x, y] of ring) {
    flat.push(x * t.scaleX + t.offsetX, y * t.scaleY + t.offsetY);
  }
  return flat;
}

