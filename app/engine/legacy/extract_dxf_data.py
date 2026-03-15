from pathlib import Path

import ezdxf
import pandas as pd

from geometry_utils import (
    all_layers,
    entity_matches_layer,
    extract_entity_text,
    load_job_config,
    polygons_from_entities,
    unit_factor,
)

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
column_labels = []
floor_numbers = []

for entity in msp:
    layer = getattr(entity.dxf, "layer", "")
    kind = entity.dxftype()

    if kind == "POINT" and layer in point_layers:
        location = entity.dxf.location
        points.append((location.x * factor, location.y * factor))
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

boundary_entities = [entity for entity in msp if entity_matches_layer(entity, boundary_layers)]
loop_polygons = polygons_from_entities(boundary_entities, factor)

points_df = pd.DataFrame(points, columns=["x", "y"])
column_labels_df = pd.DataFrame(column_labels, columns=["label", "x", "y"])
floor_numbers_df = pd.DataFrame(floor_numbers, columns=["floor_number", "x", "y"])

boundary_rows = []
for boundary_id, polygon in enumerate(loop_polygons):
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
                }
            )

boundaries_df = pd.DataFrame(
    boundary_rows,
    columns=["boundary_id", "type", "vertex_index", "x", "y", "closed", "ring_role"],
)

points_df.to_csv("dxf_points.csv", index=False)
boundaries_df.to_csv("dxf_boundaries.csv", index=False)
column_labels_df.to_csv("dxf_column_labels.csv", index=False)
floor_numbers_df.to_csv("dxf_floor_numbers.csv", index=False)

print("Points:", len(points_df))
print("Boundary loops:", boundaries_df["boundary_id"].nunique() if not boundaries_df.empty else 0)
print("Column Labels:", len(column_labels_df))
print("Floor Numbers:", len(floor_numbers_df))
print("Detected layers:", ", ".join(all_layers(doc)))
