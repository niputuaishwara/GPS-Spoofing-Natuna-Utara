import os
import pandas as pd
from detection_engine import analyze_vessel_data
from risk_engine import calculate_risk
from sklearn.metrics import f1_score

DATASETS_DIR = os.path.join("datasets", "testing")

def test_weights(weights, datasets):
    y_true = []
    y_pred = []
    score_distribution = {}
    
    for dataset_name in datasets:
        filepath = os.path.join(DATASETS_DIR, dataset_name)
        if not os.path.exists(filepath):
            print(f"Dataset {filepath} not found! Please generate it first.")
            continue
            
        df = pd.read_csv(filepath)
        prev_data = None
        
        for i, row in df.iterrows():
            current_data = row.to_dict()
            analyzed = analyze_vessel_data(current_data, prev_data)
            
            # Override weights
            risk_score, risk_level, spoofing_detected = calculate_risk(
                analyzed['speed_alert'], analyzed['course_alert'],
                analyzed['geofence_alert'], analyzed['border_alert'],
                weights=weights
            )
            
            y_true.append(int(row.get('is_anomaly', 0)))
            y_pred.append(1 if spoofing_detected else 0)
            
            score_rounded = int(risk_score)
            score_distribution[score_rounded] = score_distribution.get(score_rounded, 0) + 1
            
            prev_data = analyzed
            
    if not y_true:
        return
        
    f1 = f1_score(y_true, y_pred, zero_division=0)
    tp = sum((t == 1 and p == 1) for t, p in zip(y_true, y_pred))
    fp = sum((t == 0 and p == 1) for t, p in zip(y_true, y_pred))
    dist_str = ", ".join([f"{k}: {v}" for k, v in sorted(score_distribution.items())])
    print(f"Weights (Speed, Course, Geofence, Border): {str(weights):<20} -> F1 Score: {f1:.3f} (TP: {tp}, FP: {fp})")
    print(f"   Score Distribution (Count of Risk Scores): {dist_str}")

if __name__ == "__main__":
    print("--- Weight Sensitivity Test ---")
    datasets_to_test = [
        "mixed_attack_r25.csv",
        "mixed_attack_r50.csv",
        "mixed_attack_r75.csv",
        "mixed_attack_r100.csv"
    ]
    print(f"Datasets: {', '.join(datasets_to_test)}\n")
    
    configurations = [
        (25, 25, 25, 25), # Default Balanced
        (40, 20, 20, 20), # Speed Focused
        (10, 10, 30, 50), # Border Focused
        (34, 33, 33, 0),  # Ignore Border
    ]
    for w in configurations:
        test_weights(w, datasets_to_test)
