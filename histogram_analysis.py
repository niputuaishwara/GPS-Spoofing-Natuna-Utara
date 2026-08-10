import os
import pandas as pd
from detection_engine import analyze_vessel_data
from risk_engine import calculate_risk

DATASETS_DIR = "datasets/testing"

datasets = [
    "mixed_attack_r25.csv",
    "mixed_attack_r50.csv",
    "mixed_attack_r75.csv",
    "mixed_attack_r100.csv"
]

configurations = [
    (25, 25, 25, 25),
    (40, 20, 20, 20),
    (10, 10, 30, 50),
    (34, 33, 33, 0),
]

# We will collect all anomaly rows (is_anomaly == 1)
anomaly_rows = []

for dataset_name in datasets:
    filepath = os.path.join(DATASETS_DIR, dataset_name)
    if not os.path.exists(filepath):
        continue
    df = pd.read_csv(filepath)
    prev_data = None
    for i, row in df.iterrows():
        analyzed = analyze_vessel_data(row.to_dict(), prev_data)
        if int(row.get('is_anomaly', 0)) == 1:
            flags_active = sum([
                analyzed['speed_alert'],
                analyzed['course_alert'],
                analyzed['geofence_alert'],
                analyzed['border_alert']
            ])
            anomaly_rows.append({
                'dataset': dataset_name,
                'flags_active': flags_active,
                'analyzed': analyzed
            })
        prev_data = analyzed

print("=== DISTRIBUSI JUMLAH FLAG PADA BARIS ANOMALI (is_anomaly=1) ===")
flag_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
for r in anomaly_rows:
    flag_counts[r['flags_active']] += 1

for k in range(5):
    print(f"Jumlah baris dengan {k} flag aktif: {flag_counts[k]} baris")

print("\n=== HISTOGRAM SKOR KLASIFIKASI PER BUCKET FLAG ===")
for config in configurations:
    import risk_engine
    risk_engine.WEIGHTS = {
        'speed': config[0],
        'course': config[1],
        'geofence': config[2],
        'border': config[3]
    }
    
    print(f"\nKonfigurasi Bobot (Speed, Course, Geofence, Border): {config}")
    
    # Group by flag count
    bucket_scores = {0: {}, 1: {}, 2: {}, 3: {}, 4: {}}
    for r in anomaly_rows:
        analyzed = r['analyzed']
        score, _, _ = calculate_risk(
            analyzed['speed_alert'],
            analyzed['course_alert'],
            analyzed['geofence_alert'],
            analyzed['border_alert'],
            weights=config
        )
        score = int(score)
        f_count = r['flags_active']
        bucket_scores[f_count][score] = bucket_scores[f_count].get(score, 0) + 1
        
    for f_count in range(5):
        if flag_counts[f_count] > 0:
            dist_str = ", ".join([f"Skor {k}: {v} baris" for k, v in sorted(bucket_scores[f_count].items())])
            print(f"  [{f_count}-Flag Bucket] -> {dist_str}")

