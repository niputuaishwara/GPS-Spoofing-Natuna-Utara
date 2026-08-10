import os
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from detection_engine import analyze_vessel_data
from risk_engine import calculate_risk

DATASETS_DIR = "datasets"
OUTPUT_FILE = "datasets/full_test_summary.csv"

# 5 dataset yang diuji
DATASET_FILES = [
    "normal_route.csv",
    "sudden_jump.csv",
    "slow_drift.csv",
    "geofence_escape.csv",
    "mixed_attack.csv",
]

def determine_skenario(filename):
    if filename.startswith("normal"):
        return "Normal"
    elif "sudden_jump" in filename:
        return "Sudden Jump"
    elif "slow_drift" in filename:
        return "Slow Drift"
    elif "geofence_escape" in filename:
        return "Geofence Escape"
    elif "mixed_attack" in filename:
        return "Mixed Attack"
    return "Unknown"

def determine_variant(filename):
    if "_r25" in filename: return "R25"
    if "_r50" in filename: return "R50"
    if "_r75" in filename: return "R75"
    if "_r100" in filename: return "R100"
    return "Base"

def run_all():
    results = []
    for f in DATASET_FILES:
        filepath = os.path.join(DATASETS_DIR, "testing", f)
        if not os.path.exists(filepath):
            filepath = os.path.join(DATASETS_DIR, f)
        if not os.path.exists(filepath):
            print(f"[SKIP] File not found: {filepath}")
            continue

        df = pd.read_csv(filepath)

        speed_flags = course_flags = geofence_flags = border_flags = 0
        max_risk = total_risk = spoofed_count = 0
        risk_levels_count = {"NORMAL": 0, "LOW RISK": 0, "MEDIUM RISK": 0, "HIGH RISK": 0, "CRITICAL": 0}

        prev_data = None
        y_true = []
        y_pred = []
        for i, row in df.iterrows():
            current_data = row.to_dict()
            analyzed = analyze_vessel_data(current_data, prev_data)
            risk_score, risk_level, spoofing_detected = calculate_risk(
                analyzed['speed_alert'], analyzed['course_alert'],
                analyzed['geofence_alert'], analyzed['border_alert']
            )
            if analyzed['speed_alert']:    speed_flags += 1
            if analyzed['course_alert']:   course_flags += 1
            if analyzed['geofence_alert']: geofence_flags += 1
            if analyzed['border_alert']:   border_flags += 1
            if spoofing_detected:          spoofed_count += 1
            max_risk = max(max_risk, risk_score)
            total_risk += risk_score
            risk_levels_count[risk_level] += 1
            prev_data = analyzed
            y_true.append(int(row.get('is_anomaly', 0)))
            y_pred.append(1 if spoofing_detected else 0)

        dominant_risk = max(risk_levels_count, key=risk_levels_count.get)
        avg_risk = round(total_risk / len(df), 2)
        
        precision = round(precision_score(y_true, y_pred, zero_division=0), 3)
        recall = round(recall_score(y_true, y_pred, zero_division=0), 3)
        f1 = round(f1_score(y_true, y_pred, zero_division=0), 3)

        results.append({
            'No':             len(results) + 1,
            'Skenario':       determine_skenario(f),
            'Varian':         determine_variant(f),
            'Nama Dataset':   f,
            'Total Baris':    len(df),
            'Speed Alert':    speed_flags,
            'Course Alert':   course_flags,
            'Geofence Alert': geofence_flags,
            'Border Alert':   border_flags,
            'Avg Risk Score': avg_risk,
            'Max Risk Score': max_risk,
            'Dominant Level': dominant_risk,
            'Spoofing Count': spoofed_count,
            'Spoofing (%)':   round(spoofed_count / len(df) * 100, 1),
            'Precision':      precision,
            'Recall':         recall,
            'F1 Score':       f1
        })
        print(f"[OK] {f:40s} | Avg={avg_risk:5} | Max={max_risk:3} | Spoofed={spoofed_count:3} ({round(spoofed_count/len(df)*100,1)}%)")

    res_df = pd.DataFrame(results)
    res_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[OK] Full test completed. Results saved to: {OUTPUT_FILE}")
    print(f"   Total datasets tested: {len(results)}")

if __name__ == "__main__":
    run_all()
