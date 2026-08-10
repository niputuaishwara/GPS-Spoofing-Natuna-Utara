def calculate_risk(speed_alert: bool, course_alert: bool, geofence_alert: bool, border_alert: bool, weights=(25, 25, 25, 25)):
    """
    Calculates the risk score based on triggered alerts.
    Weights default to (25, 25, 25, 25) for Speed, Course, Geofence, Border.
    """
    risk_score = 0
    if speed_alert: risk_score += weights[0]
    if course_alert: risk_score += weights[1]
    if geofence_alert: risk_score += weights[2]
    if border_alert: risk_score += weights[3]
    
    # Risk Level determination
    if risk_score <= 25:
        risk_level = "NORMAL"
    elif risk_score <= 50:
        risk_level = "MEDIUM RISK"
    elif risk_score <= 75:
        risk_level = "HIGH RISK"
    else:
        risk_level = "CRITICAL"
        
    spoofing_detected = risk_score >= 50
    
    return risk_score, risk_level, spoofing_detected
