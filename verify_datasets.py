import os
import pandas as pd
from detection_engine import analyze_vessel_data
import itertools

DATASETS_DIR = "datasets/testing"
SCENARIOS = ['normal', 'sudden_jump', 'slow_drift', 'geofence_escape', 'mixed_attack']

def get_alerts(filepath):
    df = pd.read_csv(filepath)
    prev_data = None
    alerts = []
    
    speed_c, course_c, geofence_c, border_c = 0, 0, 0, 0
    for i, row in df.iterrows():
        analyzed = analyze_vessel_data(row.to_dict(), prev_data)
        alerts.append(analyzed)
        if analyzed['speed_alert']: speed_c += 1
        if analyzed['course_alert']: course_c += 1
        if analyzed['geofence_alert']: geofence_c += 1
        if analyzed['border_alert']: border_c += 1
        prev_data = analyzed
        
    return alerts, (speed_c, course_c, geofence_c, border_c)

print("=== STEP 2: VERIFIKASI IDENTIK SEMUA LEVEL ===")
duplicates_found = False
for risk in ['r25', 'r50', 'r75', 'r100']:
    print(f"\nMengecek Risk Level: {risk}")
    scenario_alerts = {}
    for scen in SCENARIOS:
        filepath = os.path.join(DATASETS_DIR, f"{scen}_{risk}.csv")
        alerts_list, counts = get_alerts(filepath)
        scenario_alerts[scen] = counts
        print(f"  {scen}: Speed={counts[0]}, Course={counts[1]}, Geofence={counts[2]}, Border={counts[3]}")
        
    # Check for identical counts
    for s1, s2 in itertools.combinations(SCENARIOS, 2):
        if scenario_alerts[s1] == scenario_alerts[s2]:
            print(f"  [WARNING] Alert count IDENTIK ditemukan antara {s1} dan {s2}: {scenario_alerts[s1]}")
            duplicates_found = True

if duplicates_found:
    print("\n[STOP] Ditemukan duplikasi alert count lintas skenario.")
else:
    print("\n[OK] Tidak ada alert count yang identik secara tidak wajar antar skenario untuk semua level.")

print("\n=== STEP 3: ANALISIS CONTINUATION ROW R25 & R50 ===")
for risk in ['r25', 'r50']:
    print(f"\n--- Risk Level: {risk} ---")
    for scen in SCENARIOS:
        filepath = os.path.join(DATASETS_DIR, f"{scen}_{risk}.csv")
        df = pd.read_csv(filepath)
        alerts_list, _ = get_alerts(filepath)
        
        # Find incidents (continuous blocks of is_anomaly=1)
        incidents = []
        in_incident = False
        current_start = -1
        for i, row in df.iterrows():
            if row['is_anomaly'] == 1:
                if not in_incident:
                    in_incident = True
                    current_start = i
            else:
                if in_incident:
                    incidents.append(current_start)
                    in_incident = False
        if in_incident:
            incidents.append(current_start)
            
        print(f"Skenario {scen} ({risk}) - Menemukan {len(incidents)} insiden.")
        
        # Analyze continuation rows
        retrigger_speed = 0
        retrigger_course = 0
        total_cont_rows = 0
        
        for start_idx in incidents:
            # We want up to 5 rows AFTER the start_idx that are still part of the anomaly window
            for j in range(1, 6):
                idx = start_idx + j
                if idx < len(df) and df.iloc[idx]['is_anomaly'] == 1:
                    total_cont_rows += 1
                    if alerts_list[idx]['speed_alert']: retrigger_speed += 1
                    if alerts_list[idx]['course_alert']: retrigger_course += 1
                    
        print(f"  Total Continuation Rows (is_anomaly=1): {total_cont_rows}")
        print(f"  Retrigger Speed Alert : {retrigger_speed}/{total_cont_rows}")
        print(f"  Retrigger Course Alert: {retrigger_course}/{total_cont_rows}")
