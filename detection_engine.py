from utils import haversine_distance
from geofence import check_inside_geofence
from border_analysis import calculate_distance_to_border
import datetime

# Thresholds
SPEED_THRESHOLD_KMH = 80.0  # unrealistic speed
COURSE_THRESHOLD_DEG = 45.0 # unrealistic rate of turn per step
BORDER_CHANGE_THRESHOLD_KM = 5.0 # unrealistic change in distance to border per step

def analyze_vessel_data(current_data, previous_data=None):
    """
    Analyzes vessel data and flags any anomalies.
    Returns the processed data dict including alerts.
    """
    # Initialize alerts
    speed_alert = False
    course_alert = False
    geofence_alert = False
    border_alert = False
    
    distance_travelled = 0.0
    
    lat = float(current_data['latitude'])
    lon = float(current_data['longitude'])
    timestamp = current_data['timestamp']
    course = float(current_data['sog']) if 'sog' in current_data and 'cog' not in current_data else float(current_data.get('cog', 0))
    speed_over_ground = float(current_data['sog'])

    # 1. Geofence Check
    inside_geofence = check_inside_geofence(lat, lon)
    if not inside_geofence:
        geofence_alert = True
        
    # 2. Border Proximity Check
    distance_to_border = calculate_distance_to_border(lat, lon)
    
    if previous_data is not None:
        prev_lat = float(previous_data['latitude'])
        prev_lon = float(previous_data['longitude'])
        prev_course = float(previous_data['course'])
        prev_dist_to_border = float(previous_data['distance_to_border'])
        
        # Calculate time difference in hours
        if isinstance(timestamp, str):
            curr_time = datetime.datetime.fromisoformat(timestamp)
        else:
            curr_time = timestamp
            
        if isinstance(previous_data['timestamp'], str):
            prev_time = datetime.datetime.fromisoformat(previous_data['timestamp'])
        else:
            prev_time = previous_data['timestamp']
            
        time_diff_hours = (curr_time - prev_time).total_seconds() / 3600.0
        
        # Method 1: Speed Check
        distance_travelled = haversine_distance(prev_lat, prev_lon, lat, lon)
        if time_diff_hours > 0:
            calculated_speed = distance_travelled / time_diff_hours
            if calculated_speed > SPEED_THRESHOLD_KMH:
                speed_alert = True
                
        # Method 2: Rate of Turn Check
        delta_course = abs(course - prev_course)
        # Handle wrap around 360
        if delta_course > 180:
            delta_course = 360 - delta_course
        if delta_course > COURSE_THRESHOLD_DEG:
            course_alert = True
            
        # Method 4 part 2: Border Proximity Anomaly
        delta_border_dist = abs(distance_to_border - prev_dist_to_border)
        if delta_border_dist > BORDER_CHANGE_THRESHOLD_KM:
            border_alert = True

    return {
        'timestamp': str(timestamp),
        'latitude': lat,
        'longitude': lon,
        'speed': speed_over_ground,
        'course': course,
        'distance_travelled': distance_travelled,
        'distance_to_border': distance_to_border,
        'inside_geofence': inside_geofence,
        'speed_alert': speed_alert,
        'course_alert': course_alert,
        'geofence_alert': geofence_alert,
        'border_alert': border_alert
    }
