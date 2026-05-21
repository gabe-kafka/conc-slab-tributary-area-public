from pathlib import Path

import ezdxf
import pandas as pd

from geometry_utils import (
    all_layers,
    entity_to_polygon,
    entity_matches_layer,
    extract_entity_text,
    load_job_config,
    polygons_from_entities,
    unit_factor,
)

MIN_COLUMN_FOOTPRINT_AREA_SF = 0.25
MIN_COLUMN_FOOTPRINT_DIMENSION_FT = 0.5


def is_column_footprint_candidate(polygon) -> bool:
    if polygon is None or polygon.is_empty or polygon.area < MIN_COLUMN_FOOTPRINT_AREA_SF:
        return False

    min_x, min_y, max_x, max_y = polygon.bounds
    min_dimension = min(max_x - min_x, max_y - min_y)
    return min_dimension >= MIN_COLUMN_FOOTPRINT_DIMENSION_FT


INPUT_DXF = Path("INPUT.DXF")
if not INPUT_DXF.exists():
    raise FileNotFoundError(f"Missing input DXF: {INPUT_DXF}")

doc = ezdxf.readfile(str(INPUT_DXF))
msp = doc.modelspace()
job_config = load_job_config()
factor = unit_factor(job_config["source_units"])
layers = job_config["layers"]

point_layers = set(layers["support_point"])
column_label_layers = set(layers["column_label"])
floor_label_layers = set(layers["floor_label"])
boundary_layers = set(layers["boundary"])

points = []
column_footprints = []
column_labels = []
floor_numbers = []
skipped_column_footprints = 0

for entity in msp:
    layer = getattr(entity.dxf, "layer", "")
    kind = entity.dxftype()

    if layer in point_layers:
        if kind == "POINT":
            location = entity.dxf.location
            points.append(
                {
                    "x": location.x * factor,
                    "y": location.y * factor,
                    "source_type": "POINT",
                    "source_layer": layer,
                    "footprint_id": "",
                }
            )
            continue

        polygon = entity_to_polygon(entity, factor)
        if is_column_footprint_candidate(polygon):
            footprint_id = f"CF_{len(column_footprints)}"
            centroid = polygon.centroid
            if not polygon.buffer(1e-6).covers(centroid):
                centroid = polygon.representative_point()
            points.append(
                {
                    "x": centroid.x,
                    "y": centroid.y,
                    "source_type": "FOOTPRINT",
                    "source_layer": layer,
                    "footprint_id": footprint_id,
                }
            )
            column_footprints.append(
                {
                    "footprint_id": footprint_id,
                    "source_layer": layer,
                    "polygon": polygon,
                }
            )
        elif polygon is not None and not polygon.is_empty:
            skipped_column_footprints += 1
        continue

    if kind in {"TEXT", "MTEXT"} and layer in column_label_layers:
        text = extract_entity_text(entity)
        insert = entity.dxf.insert
        if text:
            column_labels.append({"label": text, "x": insert.x * factor, "y": insert.y * factor})
        continue

    if kind in {"TEXT", "MTEXT"} and layer in floor_label_layers:
        text = extract_entity_text(entity)
        insert = entity.dxf.insert
        if text:
            floor_numbers.append({"floor_number": text, "x": insert.x * factor, "y": insert.y * factor})

loop_records = []
for boundary_layer in sorted(boundary_layers):
    boundary_entities = [
        entity for entity in msp if entity_matches_layer(entity, {boundary_layer})
    ]
    for polygon in polygons_from_entities(boundary_entities, factor):
        loop_records.append({"polygon": polygon, "load_layer": boundary_layer})

points_df = pd.DataFrame(
    points,
    columns=["x", "y", "source_type", "source_layer", "footprint_id"],
)
column_labels_df = pd.DataFrame(column_labels, columns=["label", "x", "y"])
floor_numbers_df = pd.DataFrame(floor_numbers, columns=["floor_number", "x", "y"])

boundary_rows = []
for boundary_id, record in enumerate(loop_records):
    polygon = record["polygon"]
    load_layer = record["load_layer"]
    exterior_coords = list(polygon.exterior.coords)
    for vertex_index, (x_coord, y_coord) in enumerate(exterior_coords[:-1]):
        boundary_rows.append(
            {
                "boundary_id": boundary_id,
                "type": "LWPOLYLINE",
                "vertex_index": vertex_index,
                "x": x_coord,
                "y": y_coord,
                "closed": True,
                "ring_role": "shell",
                "load_layer": load_layer,
            }
        )

    for hole_index, interior in enumerate(polygon.interiors):
        ring_boundary_id = f"{boundary_id}_H{hole_index}"
        for vertex_index, (x_coord, y_coord) in enumerate(list(interior.coords)[:-1]):
            boundary_rows.append(
                {
                    "boundary_id": ring_boundary_id,
                    "type": "LWPOLYLINE",
                    "vertex_index": vertex_index,
                    "x": x_coord,
                    "y": y_coord,
                    "closed": True,
                    "ring_role": "hole",
                    "load_layer": load_layer,
                }
            )

boundaries_df = pd.DataFrame(
    boundary_rows,
    columns=[
        "boundary_id",
        "type",
        "vertex_index",
        "x",
        "y",
        "closed",
        "ring_role",
        "load_layer",
    ],
)

footprint_rows = []
for record in column_footprints:
    polygon = record["polygon"]
    footprint_id = record["footprint_id"]
    source_layer = record["source_layer"]
    for vertex_index, (x_coord, y_coord) in enumerate(list(polygon.exterior.coords)[:-1]):
        footprint_rows.append(
            {
                "footprint_id": footprint_id,
                "source_layer": source_layer,
                "ring_role": "shell",
                "vertex_index": vertex_index,
                "x": x_coord,
                "y": y_coord,
            }
        )

    for hole_index, interior in enumerate(polygon.interiors):
        for vertex_index, (x_coord, y_coord) in enumerate(list(interior.coords)[:-1]):
            footprint_rows.append(
                {
                    "footprint_id": footprint_id,
                    "source_layer": source_layer,
                    "ring_role": f"hole_{hole_index}",
                    "vertex_index": vertex_index,
                    "x": x_coord,
                    "y": y_coord,
                }
            )

footprints_df = pd.DataFrame(
    footprint_rows,
    columns=[
        "footprint_id",
        "source_layer",
        "ring_role",
        "vertex_index",
        "x",
        "y",
    ],
)

points_df.to_csv("dxf_points.csv", index=False)
boundaries_df.to_csv("dxf_boundaries.csv", index=False)
footprints_df.to_csv("dxf_column_footprints.csv", index=False)
column_labels_df.to_csv("dxf_column_labels.csv", index=False)
floor_numbers_df.to_csv("dxf_floor_numbers.csv", index=False)

print("Points:", len(points_df))
print("Column footprints:", footprints_df["footprint_id"].nunique() if not footprints_df.empty else 0)
print("Skipped tiny column footprint candidates:", skipped_column_footprints)
print("Boundary loops:", boundaries_df["boundary_id"].nunique() if not boundaries_df.empty else 0)
print("Column Labels:", len(column_labels_df))
print("Floor Numbers:", len(floor_numbers_df))
print("Detected layers:", ", ".join(all_layers(doc)))
