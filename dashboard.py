import streamlit as st
import folium
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from database import get_all_vessel_data
from geofence import NATUNA_GEOFENCE_COORDS

SIMULATED_BORDER_LON = 111.0

# ─────────────────────────────────────────────────────────────
# Helper: Build folium map from history list
# ─────────────────────────────────────────────────────────────
def build_live_map(history: list, current: dict) -> folium.Map:
    """
    Builds a folium map showing:
    - Natuna geofence polygon
    - Simulated border line
    - Full track history (color-coded by risk)
    - Animated vessel icon at current position
    """
    lat = current['latitude']
    lon = current['longitude']

    m = folium.Map(
        location=[lat, lon],
        zoom_start=7,
        tiles='CartoDB dark_matter'
    )

    # ── Geofence Polygon ──
    # Shapely uses (lon, lat), Folium uses (lat, lon) → swap
    geo_latlon = [(coord[1], coord[0]) for coord in NATUNA_GEOFENCE_COORDS]
    folium.Polygon(
        locations=geo_latlon,
        color='#00BFFF',
        weight=2,
        fill=True,
        fill_color='#00BFFF',
        fill_opacity=0.08,
        popup='Natuna Operational Zone'
    ).add_to(m)

    # ── Border Line ──
    folium.PolyLine(
        locations=[(3.0, SIMULATED_BORDER_LON), (7.0, SIMULATED_BORDER_LON)],
        color='#FF4444',
        weight=2,
        dash_array='8 4',
        popup='⚠️ Simulated Border Line (Lon 111°)'
    ).add_to(m)

    # Border label
    folium.Marker(
        location=[7.1, SIMULATED_BORDER_LON],
        icon=folium.DivIcon(
            html='<div style="color:#FF4444;font-size:11px;font-weight:bold;white-space:nowrap;">⚠️ BORDER LINE</div>',
            icon_size=(120, 20),
            icon_anchor=(0, 0)
        )
    ).add_to(m)

    # ── Track History ──
    if len(history) > 1:
        # Draw polyline connecting all history points
        coords = [(h['latitude'], h['longitude']) for h in history]
        # Determine overall color for the line
        has_spoofing = any(h.get('spoofing_detected', False) for h in history)
        has_risk = any(h.get('risk_score', 0) > 0 for h in history)
        line_color = '#FF3333' if has_spoofing else ('#FFA500' if has_risk else '#00FF88')
        folium.PolyLine(coords, color=line_color, weight=3, opacity=0.8).add_to(m)

    # ── Individual Track Points (CircleMarkers) ──
    for h in history[:-1]:  # all but current
        risk = h.get('risk_score', 0)
        spoofed = h.get('spoofing_detected', False)
        if spoofed:
            dot_color = '#FF3333'
            radius = 5
        elif risk > 0:
            dot_color = '#FFA500'
            radius = 4
        else:
            dot_color = '#00FF88'
            radius = 3

        popup_html = (
            f"<b>Step:</b> {h.get('timestamp','')}<br>"
            f"<b>Risk:</b> {risk} ({h.get('risk_level','N/A')})<br>"
            f"<b>Lat:</b> {h['latitude']:.4f} | <b>Lon:</b> {h['longitude']:.4f}<br>"
            f"<b>SOG:</b> {h.get('speed', 0):.1f} knots | <b>COG:</b> {h.get('course', 0):.1f}°"
        )

        folium.CircleMarker(
            location=[h['latitude'], h['longitude']],
            radius=radius,
            color=dot_color,
            fill=True,
            fill_color=dot_color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=220)
        ).add_to(m)

    # ── Current Position (Vessel Icon) ──
    risk_score = current.get('risk_score', 0)
    spoofing = current.get('spoofing_detected', False)

    if spoofing:
        vessel_color = '#FF0000'
        glow = 'rgba(255,0,0,0.6)'
        status_label = '🚨 SPOOFING'
    elif risk_score > 0:
        vessel_color = '#FFA500'
        glow = 'rgba(255,165,0,0.5)'
        status_label = '⚠️ ALERT'
    else:
        vessel_color = '#00FF88'
        glow = 'rgba(0,255,136,0.4)'
        status_label = '✅ NORMAL'

    vessel_html = f"""
    <div style="position:relative;">
      <div style="
        width:22px;height:22px;
        background:{vessel_color};
        border-radius:50%;
        border:2px solid white;
        box-shadow:0 0 12px 4px {glow};
        display:flex;align-items:center;justify-content:center;
        font-size:12px;
      ">⛵</div>
      <div style="
        position:absolute;top:-22px;left:26px;
        background:rgba(0,0,0,0.75);
        color:{vessel_color};
        padding:2px 6px;border-radius:4px;
        font-size:10px;font-weight:bold;white-space:nowrap;
      ">{status_label}</div>
    </div>
    """

    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(html=vessel_html, icon_size=(80, 40), icon_anchor=(11, 11)),
        popup=folium.Popup(
            f"<b>CURRENT POSITION</b><br>Risk Score: {risk_score}<br>"
            f"Lat: {lat:.4f} | Lon: {lon:.4f}", max_width=200
        )
    ).add_to(m)

    return m


# ─────────────────────────────────────────────────────────────
# Helper: Build risk gauge
# ─────────────────────────────────────────────────────────────
def build_gauge(risk_score: int) -> go.Figure:
    if risk_score >= 75:
        bar_color = '#FF3333'
    elif risk_score >= 50:
        bar_color = '#FF8C00'
    elif risk_score >= 25:
        bar_color = '#FFD700'
    else:
        bar_color = '#00CC66'

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_score,
        number={'font': {'size': 36, 'color': bar_color}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#888', 'tickfont': {'color': '#aaa'}},
            'bar': {'color': bar_color, 'thickness': 0.25},
            'bgcolor': '#1a1a2e',
            'borderwidth': 0,
            'steps': [
                {'range': [0, 25],  'color': '#0d2b1a'},
                {'range': [25, 50], 'color': '#2b2b0d'},
                {'range': [50, 75], 'color': '#2b1a0d'},
                {'range': [75, 100],'color': '#2b0d0d'},
            ],
            'threshold': {
                'line': {'color': bar_color, 'width': 3},
                'thickness': 0.8,
                'value': risk_score
            }
        }
    ))
    fig.update_layout(
        height=220,
        margin=dict(t=20, b=0, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


# ─────────────────────────────────────────────────────────────
# Static Dashboard (post-analysis summary view)
# ─────────────────────────────────────────────────────────────
def render_dashboard(user: dict = None):
    user_id = user['id'] if user else None
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
        border: 1px solid #2a2a5e;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .metric-label { color: #8888aa; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #e0e0ff; font-size: 20px; font-weight: bold; }
    .alert-box {
        background: linear-gradient(135deg, #3a0000, #1a0000);
        border: 2px solid #ff3333;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
        animation: pulse 1s infinite;
    }
    @keyframes pulse { 0%,100% { border-color:#ff3333; } 50% { border-color:#ff9999; } }
    </style>
    """, unsafe_allow_html=True)

    data = get_all_vessel_data(user_id=user_id)
    if not data:
        st.info("Belum ada data. Jalankan simulasi atau upload file terlebih dahulu.")
        return

    df = pd.DataFrame(data)
    latest = df.iloc[-1]

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.markdown("#### 📍 Current Position")
        for label, val in [
            ("Latitude", f"{latest['latitude']:.5f}°"),
            ("Longitude", f"{latest['longitude']:.5f}°"),
            ("Speed (SOG)", f"{latest['speed']:.2f} knots"),
            ("Course (COG)", f"{latest['course']:.1f}°"),
            ("Distance to Border", f"{latest['distance_to_border']:.2f} km"),
            ("Inside Geofence", "✅ YES" if latest['inside_geofence'] else "❌ NO"),
        ]:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{label}</div>
              <div class="metric-value">{val}</div>
            </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("#### 🗺️ Vessel Track Map")
        m = build_live_map(df.to_dict('records'), latest.to_dict())
        from streamlit_folium import st_folium
        st_folium(m, width=None, height=480, returned_objects=[])

    with col3:
        st.markdown("#### 🎯 Risk Assessment")
        st.plotly_chart(build_gauge(int(latest['risk_score'])), use_container_width=True)

        risk_colors = {'NORMAL': '#00CC66', 'LOW RISK': '#FFD700', 'MEDIUM RISK': '#FF8C00', 'HIGH RISK': '#FF3333'}
        rc = risk_colors.get(latest['risk_level'], '#888')
        st.markdown(f"""
        <div style="text-align:center;padding:8px;border-radius:8px;
             border:2px solid {rc};background:rgba(0,0,0,0.3);margin-bottom:10px;">
          <span style="color:{rc};font-size:16px;font-weight:bold;">{latest['risk_level']}</span>
        </div>""", unsafe_allow_html=True)

        if latest['spoofing_detected']:
            reasons = []
            if latest['speed_alert']:    reasons.append("⚡ Speed Anomaly")
            if latest['course_alert']:   reasons.append("🔄 Course Anomaly")
            if latest['geofence_alert']: reasons.append("🚧 Geofence Violation")
            if latest['border_alert']:   reasons.append("🌐 Border Proximity")
            st.markdown(f"""
            <div class="alert-box">
              <div style="color:#FF3333;font-size:14px;font-weight:bold;">🚨 GPS SPOOFING DETECTED</div>
              <div style="color:#ffaaaa;font-size:12px;margin-top:6px;">{'<br>'.join(reasons)}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:10px;border-radius:8px;
                 border:2px solid #00CC66;background:rgba(0,80,0,0.15);">
              <span style="color:#00CC66;font-size:13px;font-weight:bold;">✅ NO SPOOFING DETECTED</span>
            </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 📈 Analytics Charts")
    tab1, tab2, tab3, tab4 = st.tabs(["Risk Score", "Distance to Border", "Speed", "Course"])
    chart_cfg = dict(template='plotly_dark', height=280)
    with tab1:
        st.plotly_chart(px.line(df, x='timestamp', y='risk_score', title='Risk Score Over Time', **chart_cfg), use_container_width=True)
    with tab2:
        st.plotly_chart(px.line(df, x='timestamp', y='distance_to_border', title='Distance to Border Over Time', **chart_cfg), use_container_width=True)
    with tab3:
        st.plotly_chart(px.line(df, x='timestamp', y='speed', title='Speed (SOG) Over Time', **chart_cfg), use_container_width=True)
    with tab4:
        st.plotly_chart(px.line(df, x='timestamp', y='course', title='Course (COG) Over Time', **chart_cfg), use_container_width=True)

    spoofed_df = df[df['risk_score'] > 0][['timestamp','latitude','longitude','risk_score','risk_level','speed_alert','course_alert','geofence_alert','border_alert']]
    if not spoofed_df.empty:
        st.markdown("#### 🚨 Alert Events")
        st.dataframe(spoofed_df, use_container_width=True)
