import os
import pandas as pd
from detection_engine import analyze_vessel_data
from risk_engine import calculate_risk

DATASETS_DIR = "datasets/testing"

scenarios_r100 = [
    ("Normal", "normal_r100.csv"),
    ("Sudden Jump", "sudden_jump_r100.csv"),
    ("Slow Drift", "slow_drift_r100.csv"),
    ("Geofence Escape", "geofence_escape_r100.csv"),
    ("Mixed Attack", "mixed_attack_r100.csv"),
]

print("=== CONFUSION MATRIX PER SKENARIO (R100) ===\n")

for name, filename in scenarios_r100:
    filepath = os.path.join(DATASETS_DIR, filename)
    df = pd.read_csv(filepath)
    
    tp, fp, tn, fn = 0, 0, 0, 0
    prev_data = None
    
    for i, row in df.iterrows():
        analyzed = analyze_vessel_data(row.to_dict(), prev_data)
        risk_score, _, spoofing_detected = calculate_risk(
            analyzed['speed_alert'], analyzed['course_alert'],
            analyzed['geofence_alert'], analyzed['border_alert']
        )
        
        actual = int(row.get('is_anomaly', 0))
        predicted = 1 if spoofing_detected else 0
        
        if actual == 1 and predicted == 1: tp += 1
        elif actual == 0 and predicted == 1: fp += 1
        elif actual == 0 and predicted == 0: tn += 1
        elif actual == 1 and predicted == 0: fn += 1
        
        prev_data = analyzed
    
    total_anomaly = tp + fn
    total_normal = tn + fp
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"--- {name} ({filename}) ---")
    print(f"  Total baris: {len(df)} | Anomali: {total_anomaly} | Normal: {total_normal}")
    print(f"  TP={tp}  FP={fp}  TN={tn}  FN={fn}")
    print(f"  Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}")
    print()
