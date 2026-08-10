import os
import pandas as pd
import time
from detection_engine import analyze_vessel_data
from risk_engine import calculate_risk

DATASETS_DIR = "datasets"

def test_latency(dataset_name="normal_r25.csv"):
    filepath = os.path.join(DATASETS_DIR, dataset_name)
    if not os.path.exists(filepath):
        print(f"Dataset {dataset_name} not found!")
        return
        
    df = pd.read_csv(filepath)
    # Duplicate rows to simulate a large stream (e.g., ~10,000 rows)
    df_large = pd.concat([df]*100, ignore_index=True)
    
    prev_data = None
    latencies = []
    
    print(f"Starting latency test on {len(df_large)} rows...")
    start_total = time.perf_counter()
    
    for i, row in df_large.iterrows():
        current_data = row.to_dict()
        
        t0 = time.perf_counter()
        
        analyzed = analyze_vessel_data(current_data, prev_data)
        risk_score, risk_level, spoofing_detected = calculate_risk(
            analyzed['speed_alert'], analyzed['course_alert'],
            analyzed['geofence_alert'], analyzed['border_alert']
        )
        
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000) # in milliseconds
        
        prev_data = analyzed
        
    end_total = time.perf_counter()
    total_time_sec = end_total - start_total
    
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)
    throughput = len(df_large) / total_time_sec
    
    print("\n--- Latency Test Results ---")
    print(f"Total Rows Processed : {len(df_large):,}")
    print(f"Total Execution Time : {total_time_sec:.4f} seconds")
    print(f"Average Latency/row  : {avg_latency:.4f} ms")
    print(f"Max Latency/row      : {max_latency:.4f} ms")
    print(f"Min Latency/row      : {min_latency:.4f} ms")
    print(f"Throughput           : {throughput:,.0f} rows/second")
    print("Real-time Feasibility: YES" if throughput > 1000 else "Real-time Feasibility: MARGINAL")

if __name__ == "__main__":
    test_latency()
