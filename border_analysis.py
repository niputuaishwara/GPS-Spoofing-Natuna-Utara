from utils import haversine_distance

SIMULATED_BORDER_LON = 111.0

def calculate_distance_to_border(lat: float, lon: float) -> float:
    """
    Calculate the distance from the current position to the simulated border.
    The border is simulated as a vertical line at Longitude = 111.
    """
    return haversine_distance(lat, lon, lat, SIMULATED_BORDER_LON)
