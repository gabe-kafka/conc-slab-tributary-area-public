"use client";

import { useCallback, useMemo, useState } from "react";
import TributaryCanvas from "./canvas/TributaryCanvas";
import type { ColumnData, GeometryPayload, ProcessResult, WallData } from "@/lib/types";

interface ResultsViewProps {
  result: ProcessResult;
  geometry: GeometryPayload;
}

export default function ResultsView({ result, geometry }: ResultsViewProps) {
  const [visibleFloors, setVisibleFloors] = useState<Set<string>>(
    () => new Set(geometry.floors.map((f) => f.floor_id)),
  );
  const [selectedColumn, setSelectedColumn] = useState<{
    floorId: string;
    colIndex: number;
  } | null>(null);
  const [selectedWall, setSelectedWall] = useState<{
    floorId: string;
    wallIndex: number;
  } | null>(null);
  const [hoveredColumn, setHoveredColumn] = useState<{
    floorId: string;
    colIndex: number;
  } | null>(null);

  const toggleFloor = useCallback((floorId: string) => {
    setVisibleFloors((prev) => {
      const next = new Set(prev);
      if (next.has(floorId)) {
        next.delete(floorId);
      } else {
        next.add(floorId);
      }
      return next;
    });
  }, []);

  const handleSelectColumn = useCallback(
    (floorId: string, colIndex: number) => {
      setSelectedWall(null);
      setSelectedColumn((prev) =>
        prev?.floorId === floorId && prev?.colIndex === colIndex
          ? null
          : { floorId, colIndex },
      );
    },
    [],
  );

  const handleSelectWall = useCallback(
    (floorId: string, wallIndex: number) => {
      setSelectedColumn(null);
      setSelectedWall((prev) =>
        prev?.floorId === floorId && prev?.wallIndex === wallIndex
          ? null
          : { floorId, wallIndex },
      );
    },
    [],
  );

  const handleHoverColumn = useCallback(
    (floorId: string | null, colIndex: number | null) => {
      if (floorId === null || colIndex === null) {
        setHoveredColumn(null);
      } else {
        setHoveredColumn({ floorId, colIndex });
      }
    },
    [],
  );

  // Find selected item data
  const selectedData = useMemo(() => {
    if (selectedColumn) {
      const floor = geometry.floors.find(
        (f) => f.floor_id === selectedColumn.floorId,
      );
      const col = floor?.columns.find(
        (c) => c.index === selectedColumn.colIndex,
      );
      if (floor && col) return { type: "column" as const, floor, col };
    }
    if (selectedWall) {
      const floor = geometry.floors.find(
        (f) => f.floor_id === selectedWall.floorId,
      );
      const wall = floor?.walls.find(
        (w) => w.wall_index === selectedWall.wallIndex,
      );
      if (floor && wall) return { type: "wall" as const, floor, wall };
    }
    return null;
  }, [selectedColumn, selectedWall, geometry]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Top bar */}
      <div className="h-9 flex items-center justify-between px-3 border-b border-border-panel bg-bg-surface">
        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-text-muted">
            {geometry.floor_count} floor(s)
          </span>
          <span className="text-text-muted">|</span>
          <span className="text-text-muted">
            {geometry.floors.reduce((n, f) => n + f.columns.length, 0)} columns
          </span>
        </div>
        <div className="flex items-center gap-2">
          {result.artifacts.dxf_url && (
            <a
              href={`/api/download?url=${encodeURIComponent(result.artifacts.dxf_url)}`}
              className="px-3 py-0.5 text-[10px] uppercase tracking-wider border border-border-panel text-text-secondary hover:text-text-primary hover:border-text-muted transition-colors"
            >
              DXF
            </a>
          )}
          {result.artifacts.xlsx_url && (
            <a
              href={`/api/download?url=${encodeURIComponent(result.artifacts.xlsx_url)}`}
              className="px-3 py-0.5 text-[10px] uppercase tracking-wider border border-border-panel text-text-secondary hover:text-text-primary hover:border-text-muted transition-colors"
            >
              XLSX
            </a>
          )}
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Floor selector (left) */}
        <div className="w-36 border-r border-border-panel bg-bg-surface p-2 flex flex-col gap-1 overflow-auto">
          <div className="text-[10px] uppercase tracking-wider text-text-muted px-1 pb-1">
            Floors
          </div>
          {geometry.floors.map((floor) => {
            const active = visibleFloors.has(floor.floor_id);
            return (
              <button
                key={floor.floor_id}
                onClick={() => toggleFloor(floor.floor_id)}
                className={`text-left px-2 py-1 text-[11px] transition-colors ${
                  active
                    ? "text-text-primary bg-bg-panel"
                    : "text-text-muted hover:text-text-secondary"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="truncate">{floor.floor_id}</span>
                  <span className="text-[10px] text-text-muted">
                    {floor.columns.length}c
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Canvas (center) */}
        <TributaryCanvas
          floors={geometry.floors}
          bounds={geometry.bounds}
          visibleFloors={visibleFloors}
          selectedColumn={selectedColumn}
          hoveredColumn={hoveredColumn}
          onSelectColumn={handleSelectColumn}
          onHoverColumn={handleHoverColumn}
          onSelectWall={handleSelectWall}
        />

        {/* Info panel (right) */}
        <div className="w-56 border-l border-border-panel bg-bg-surface p-3 overflow-auto">
          <div className="text-[10px] uppercase tracking-wider text-text-muted pb-2">
            Details
          </div>
          {selectedData ? (
            selectedData.type === "column" ? (
              <ColumnInfo
                col={selectedData.col}
                floorId={selectedData.floor.floor_id}
              />
            ) : (
              <WallInfo
                wall={selectedData.wall}
                floorId={selectedData.floor.floor_id}
              />
            )
          ) : (
            <div className="text-text-muted text-[11px] pt-4">
              Click a tributary region to see details.
            </div>
          )}

          {/* Summary table for selected floor */}
          {selectedData && (
            <div className="mt-4 pt-3 border-t border-border-subtle">
              <div className="text-[10px] uppercase tracking-wider text-text-muted pb-2">
                Floor Summary
              </div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-text-muted">Columns</span>
                  <span className="text-text-primary">
                    {selectedData.floor.columns.length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Walls</span>
                  <span className="text-text-primary">
                    {selectedData.floor.walls.length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Perimeter</span>
                  <span className="text-text-primary">
                    {selectedData.floor.facade_perimeter_ft} ft
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ColumnInfo({
  col,
  floorId,
}: {
  col: ColumnData;
  floorId: string;
}) {
  const rows = [
    { label: "Label", value: col.label },
    { label: "Floor", value: floorId },
    { label: "Area", value: `${col.area_sf_ceil} SF` },
    { label: "Area (exact)", value: `${col.area_sf} SF` },
    { label: "Facade", value: `${col.facade_length_ft} ft` },
    {
      label: "Position",
      value: `(${col.point[0].toFixed(1)}, ${col.point[1].toFixed(1)})`,
    },
  ];

  return (
    <div className="space-y-1.5">
      <div className="text-accent text-sm font-medium">{col.label}</div>
      {rows.map((r) => (
        <div key={r.label} className="flex justify-between text-[11px]">
          <span className="text-text-muted">{r.label}</span>
          <span className="text-text-primary">{r.value}</span>
        </div>
      ))}
    </div>
  );
}

function WallInfo({
  wall,
  floorId,
}: {
  wall: WallData;
  floorId: string;
}) {
  const rows = [
    { label: "Wall", value: `#${wall.wall_index}` },
    { label: "Floor", value: floorId },
    { label: "Area", value: `${wall.area_sf_ceil} SF` },
    { label: "Area (exact)", value: `${wall.area_sf} SF` },
  ];

  return (
    <div className="space-y-1.5">
      <div className="text-error/80 text-sm font-medium">
        Wall {wall.wall_index}
      </div>
      {rows.map((r) => (
        <div key={r.label} className="flex justify-between text-[11px]">
          <span className="text-text-muted">{r.label}</span>
          <span className="text-text-primary">{r.value}</span>
        </div>
      ))}
    </div>
  );
}
