// --- Draft / Upload ---

export interface LayerCounts {
  [layerName: string]: { [entityType: string]: number };
}

export interface DraftData {
  id: string;
  filename: string;
  layers: string[];
  layer_counts: LayerCounts;
  suggestions: { [role: string]: string[] };
  inferred_floor_area_sf: number;
  require_unit_confirmation: boolean;
}

export interface LayerMapping {
  boundary: string[];
  wall: string[];
  support_point: string[];
  column_label: string[];
  floor_label: string[];
}

// --- Job ---

export interface JobData {
  id: string;
  session_id: string;
  draft_id: string;
  input_filename: string;
  source_units: string;
  layer_mapping: LayerMapping;
  status: "queued" | "running" | "completed" | "failed" | "needs_review";
  created_at: string;
  updated_at: string;
  warnings: string[];
  error_message: string;
  logs: string[];
  artifacts: { [name: string]: string };
}

// --- Geometry (canvas rendering) ---

export interface GeoJsonPolygon {
  type: "Polygon";
  coordinates: number[][][];
}

export interface GeoJsonMultiPolygon {
  type: "MultiPolygon";
  coordinates: number[][][][];
}

export interface GeoJsonLineString {
  type: "LineString";
  coordinates: number[][];
}

export interface GeoJsonPoint {
  type: "Point";
  coordinates: number[];
}

export type GeoJsonGeometry =
  | GeoJsonPolygon
  | GeoJsonMultiPolygon
  | GeoJsonLineString
  | GeoJsonPoint;

export interface ColumnData {
  index: number;
  label: string;
  point: [number, number];
  tributary_region: GeoJsonPolygon | GeoJsonMultiPolygon | null;
  area_sf: number;
  area_sf_ceil: number;
  facade_length_ft: number;
}

export interface WallData {
  wall_index: number;
  wall_line: GeoJsonLineString | null;
  tributary_region: GeoJsonPolygon | GeoJsonMultiPolygon | null;
  area_sf: number;
  area_sf_ceil: number;
}

export interface FacadeSegment {
  label: string;
  type: "column" | "wall";
  length_ft: number;
  polyline: number[][];
}

export interface FloorData {
  floor_id: string;
  floor_index: number;
  slab_boundary: GeoJsonPolygon | GeoJsonMultiPolygon | null;
  columns: ColumnData[];
  walls: WallData[];
  facade_segments: FacadeSegment[];
  facade_perimeter_ft: number;
}

export interface GeometryBounds {
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
}

export interface GeometryPayload {
  floors: FloorData[];
  bounds: GeometryBounds;
  floor_count: number;
}
