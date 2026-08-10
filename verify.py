import pandas as pd
from detection_engine import analyze_vessel_data
from risk_engine import calculate_risk

def check_file(filename):
    print(f'--- File: {filename} ---')
    df = pd.read_csv(f'datasets/testing/{filename}')
    prev = None
    for i, row in df.iterrows():
        c = row.to_dict()
        a = analyze_vessel_data(c, prev)
        r, lvl, sp = calculate_risk(a['speed_alert'], a['course_alert'], a['geofence_alert'], a['border_alert'])
        if r == 100:
            print(f'Row {i+1} (1-indexed): is_anomaly={c.get(\"is_anomaly\", None)}')
            print(f'  Flags: Speed={a[\"speed_alert\"]}, Course={a[\"course_alert\"]}, Geo={a[\"geofence_alert\"]}, Border={a[\"border_alert\"]}')
            print(f'  Prev Lat/Lon: {prev[\"latitude\"] if prev else None}/{prev[\"longitude\"] if prev else None}')
            print(f'  Curr Lat/Lon: {a[\"latitude\"]}/{a[\"longitude\"]}')
        prev = a

check_file('geofence_escape_r25.csv')
check_file('mixed_attack_r25.csv')
