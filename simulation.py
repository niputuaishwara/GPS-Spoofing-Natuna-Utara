import pandas as pd
import datetime
import random
import os

DATASETS_DIR = "datasets"

def generate_normal_route():
    data = []
    base_time = datetime.datetime(2026, 1, 1, 10, 0, 0)
    lat, lon = 4.1234, 108.1234
    for i in range(100):
        data.append({
            'timestamp': base_time + datetime.timedelta(seconds=i*60),
            'latitude': lat,
            'longitude': lon,
            'sog': 12.0 + random.uniform(-0.5, 0.5),
            'cog': 90.0 + random.uniform(-2, 2)
        })
        # move slightly east
        lon += 0.005
    
    os.makedirs(DATASETS_DIR, exist_ok=True)
    filepath = f"{DATASETS_DIR}/normal_route.csv"
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    return filepath

def generate_sudden_jump_attack():
    data = []
    base_time = datetime.datetime(2026, 1, 1, 10, 0, 0)
    lat, lon = 4.1234, 108.1234
    for i in range(100):
        # sudden jump at step 50
        if i == 50:
            lat += 1.0 # Huge jump
            lon += 1.0
        
        data.append({
            'timestamp': base_time + datetime.timedelta(seconds=i*60),
            'latitude': lat,
            'longitude': lon,
            'sog': 12.0,
            'cog': 90.0
        })
        if i < 50:
            lon += 0.005
        else:
            lon += 0.005 # keep moving from new jumped position
    
    os.makedirs(DATASETS_DIR, exist_ok=True)
    filepath = f"{DATASETS_DIR}/sudden_jump.csv"
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    return filepath

def generate_slow_drift_attack():
    data = []
    base_time = datetime.datetime(2026, 1, 1, 10, 0, 0)
    lat, lon = 4.1234, 108.1234
    for i in range(100):
        if i > 30:
            cog = 90.0 + (i - 30)*2.0 
        else:
            cog = 90.0
            
        data.append({
            'timestamp': base_time + datetime.timedelta(seconds=i*60),
            'latitude': lat,
            'longitude': lon,
            'sog': 12.0,
            'cog': cog
        })
        lon += 0.005
    
    os.makedirs(DATASETS_DIR, exist_ok=True)
    filepath = f"{DATASETS_DIR}/slow_drift.csv"
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    return filepath

def generate_geofence_escape():
    data = []
    base_time = datetime.datetime(2026, 1, 1, 10, 0, 0)
    lat, lon = 6.9, 110.9 # Close to boundary
    for i in range(100):
        data.append({
            'timestamp': base_time + datetime.timedelta(seconds=i*60),
            'latitude': lat,
            'longitude': lon,
            'sog': 15.0,
            'cog': 45.0
        })
        # move north-east, will quickly escape geofence (107-111, 3-7)
        lat += 0.005
        lon += 0.005
    
    os.makedirs(DATASETS_DIR, exist_ok=True)
    filepath = f"{DATASETS_DIR}/geofence_escape.csv"
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    return filepath
