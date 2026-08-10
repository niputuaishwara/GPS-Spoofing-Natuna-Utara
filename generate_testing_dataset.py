import pandas as pd
import datetime
import random
import os

OUTPUT_DIR = "datasets/testing"
ROWS_PER_FILE = 100

def ts(base_hour, offset_min):
    base = datetime.datetime(2026, 2, 1, 0, 0, 0) + datetime.timedelta(hours=base_hour)
    return base + datetime.timedelta(minutes=offset_min)

def in_natuna(lat, lon):
    return 107.0 < lon < 111.0 and 3.0 < lat < 7.0

def generate_scenario_data(scenario, n=ROWS_PER_FILE):
    random.seed(f"seed_{scenario}")
    rows = []
    
    true_lat, true_lon, true_cog = 4.5, 107.5, 90.0
    
    base_hours = {
        'normal_route': 0, 'sudden_jump': 2, 'slow_drift': 4,
        'geofence_escape': 6, 'mixed_attack': 8
    }
    base_h = base_hours.get(scenario, 0)
    
    t_offset = 0

    spoofed_remaining = 0
    was_spoofed_last_step = False
    spoof_lat = 0
    spoof_lon = 0
    spoof_cog = 0

    for i in range(n):
        t = ts(base_h, t_offset)
        
        # Advance True Physical State
        true_lon += 0.001
        true_lat += random.uniform(-0.0001, 0.0001)
        true_cog = 90.0 + random.uniform(-2, 2)
        if true_lon > 110.8: true_lon = 107.5
        if not in_natuna(true_lat, true_lon): true_lat, true_lon = 4.5, 107.5

        start_anomaly = False
        # Inject anomaly between row 20 and 80, only for anomalous scenarios
        if scenario != 'normal_route' and spoofed_remaining == 0:
            if 20 <= i <= 80 and random.random() < 0.05:
                start_anomaly = True

        if start_anomaly:
            eff_scenario = scenario
            if eff_scenario == 'mixed_attack':
                eff_scenario = random.choice(['sudden_jump', 'slow_drift', 'geofence_escape'])
                
            spoof_lat = true_lat
            spoof_lon = true_lon
            spoof_cog = true_cog
            
            if eff_scenario == 'sudden_jump':
                spoofed_remaining = random.randint(3, 5)
                spoof_lat = true_lat + random.uniform(1.0, 2.0) # Jump
            elif eff_scenario == 'slow_drift':
                spoofed_remaining = random.randint(10, 15)
                spoof_cog = (true_cog + random.uniform(20, 40)) % 360 # Drift course
            elif eff_scenario == 'geofence_escape':
                spoofed_remaining = random.randint(15, 25)
                spoof_lat = round(random.uniform(7.1, 7.8), 6) # Outside geofence (lat > 7.0)
                
            r = {
                'timestamp': t,
                'latitude': round(spoof_lat, 6),
                'longitude': round(spoof_lon, 6),
                'sog': round(random.uniform(20.0, 30.0) if eff_scenario == 'sudden_jump' else random.uniform(10.0, 14.0), 4),
                'cog': round(spoof_cog, 4),
                'is_anomaly': 1
            }
            rows.append(r)
            was_spoofed_last_step = True
            
        elif spoofed_remaining > 0:
            spoofed_remaining -= 1
            # Continue spoofed trajectory
            spoof_lon += 0.001
            spoof_lat += random.uniform(-0.0001, 0.0001)
            spoof_cog += random.uniform(-1, 1)
            r = {
                'timestamp': t,
                'latitude': round(spoof_lat, 6),
                'longitude': round(spoof_lon, 6),
                'sog': round(random.uniform(10.0, 14.0), 4),
                'cog': round(spoof_cog, 4),
                'is_anomaly': 1
            }
            rows.append(r)
            was_spoofed_last_step = True
        else:
            is_recovery_step = was_spoofed_last_step
            was_spoofed_last_step = False
            
            r = {
                'timestamp': t,
                'latitude': round(true_lat, 6),
                'longitude': round(true_lon, 6),
                'sog': round(random.uniform(10.0, 14.0), 4),
                'cog': round(true_cog, 4),
                'is_anomaly': 1 if is_recovery_step else 0
            }
            rows.append(r)

        t_offset += 1
    return rows

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    scenarios = ['normal_route', 'sudden_jump', 'slow_drift', 'geofence_escape', 'mixed_attack']

    print("[START] Generating 5 core testing datasets (100 rows each)...")
    print(f"Output dir: {OUTPUT_DIR}\n")

    total_files = 0
    total_rows  = 0

    for scenario in scenarios:
        filename = f"{scenario}.csv"
        path = os.path.join(OUTPUT_DIR, filename)
        rows = generate_scenario_data(scenario)
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        total_files += 1
        total_rows += len(df)
        print(f"  Generated {filename}: {len(df)} rows | {size_mb:.4f} MB")

    print(f"\n[DONE] Generated {total_files} files with a total of {total_rows} rows.")
