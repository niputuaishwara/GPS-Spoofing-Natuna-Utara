import os
import pandas as pd
from detection_engine import analyze_vessel_data
from risk_engine import calculate_risk

TESTING_DIR = "datasets/testing"
OUTPUT_FILE = "datasets/testing_summary.csv"

def determine_ground_truth(row_data):
    """
    Returns True if the row is INTENTIONALLY an anomaly (spoofing) based on generator logic.
    """
    return row_data.get('is_anomaly', 0) == 1

def run_tests():
    files = [f for f in os.listdir(TESTING_DIR) if f.endswith('.csv')]
    results = []
    
    for f in files:
        filepath = os.path.join(TESTING_DIR, f)
        df = pd.read_csv(filepath)
        
        speed_flags = 0
        course_flags = 0
        geofence_flags = 0
        border_flags = 0
        
        max_risk = 0
        total_risk = 0
        spoofed_count = 0
        
        risk_levels_count = {"NORMAL": 0, "LOW RISK": 0, "MEDIUM RISK": 0, "HIGH RISK": 0, "CRITICAL": 0}
        
        TP = 0
        FP = 0
        TN = 0
        FN = 0
        
        prev_data = None
        for i, row in df.iterrows():
            current_data = row.to_dict()
            analyzed = analyze_vessel_data(current_data, prev_data)
            
            risk_score, risk_level, spoofing_detected = calculate_risk(
                analyzed['speed_alert'],
                analyzed['course_alert'],
                analyzed['geofence_alert'],
                analyzed['border_alert']
            )
            
            # Count flags
            if analyzed['speed_alert']: speed_flags += 1
            if analyzed['course_alert']: course_flags += 1
            if analyzed['geofence_alert']: geofence_flags += 1
            if analyzed['border_alert']: border_flags += 1
            
            if spoofing_detected: spoofed_count += 1
            
            max_risk = max(max_risk, risk_score)
            total_risk += risk_score
            risk_levels_count[risk_level] += 1
            
            # Metrics
            is_anomaly_gt = determine_ground_truth(current_data)
            if is_anomaly_gt:
                if spoofing_detected: TP += 1
                else: FN += 1
            else:
                if spoofing_detected: FP += 1
                else: TN += 1
                
            prev_data = analyzed
            
        dominant_risk = max(risk_levels_count, key=risk_levels_count.get)
        
        results.append({
            'Filename': f,
            'Total_Rows': len(df),
            'Speed_Alerts': speed_flags,
            'Course_Alerts': course_flags,
            'Geofence_Alerts': geofence_flags,
            'Border_Alerts': border_flags,
            'Avg_Risk_Score': round(total_risk / len(df), 2),
            'Max_Risk_Score': max_risk,
            'Dominant_Level': dominant_risk,
            'Spoofing_Count': spoofed_count,
            'Spoofing_Pct': round(spoofed_count / len(df) * 100, 2),
            'TP': TP,
            'FP': FP,
            'TN': TN,
            'FN': FN
        })
        
    res_df = pd.DataFrame(results)
    res_df.sort_values(by="Filename", inplace=True)
    res_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Batch test completed. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_tests()
