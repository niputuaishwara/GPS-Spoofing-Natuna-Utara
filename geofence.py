from shapely.geometry import Point, Polygon

# Example Polygon for Natuna Operational Zone:
# (107.0,3.0), (111.0,3.0), (111.0,7.0), (107.0,7.0)
NATUNA_GEOFENCE_COORDS = [
    (107.0, 3.0),
    (111.0, 3.0),
    (111.0, 7.0),
    (107.0, 7.0)
]

NATUNA_POLYGON = Polygon(NATUNA_GEOFENCE_COORDS)

def check_inside_geofence(lat: float, lon: float) -> bool:
    """
    Check if a given latitude and longitude are inside the Natuna Operational Zone.
    """
    point = Point(lon, lat)  # shapely uses (x, y) which is (lon, lat)
    return NATUNA_POLYGON.contains(point)
