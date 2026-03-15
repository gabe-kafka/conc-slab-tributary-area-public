import pandas as pd

# Load the point data from CSV
points_df = pd.read_csv("dxf_points.csv")

# Load the boundary data
try:
    boundaries_df = pd.read_csv("dxf_boundaries.csv")
except FileNotFoundError:
    boundaries_df = pd.DataFrame()

# Preview the first few rows of each
print("✅ POINTS CSV:")
print(points_df.head())

if not boundaries_df.empty:
    print("\n✅ BOUNDARIES CSV:")
    print(boundaries_df.head())
else:
    print("\n⚠️ No boundaries found in dxf_boundaries.csv.")