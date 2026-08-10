import streamlit as st
import pandas as pd
import time
import datetime
import uuid

from database import (init_db, clear_data, insert_vessel_data, insert_log,
                      get_all_vessel_data)
from data_loader import load_dataset, load_from_upload
from detection_engine import analyze_vessel_data
from risk_engine import calculate_risk
from simulation import (generate_normal_route, generate_sudden_jump_attack,
                        generate_slow_drift_attack, generate_geofence_escape)
from dashboard import render_dashboard, build_live_map, build_gauge
from report import render_report
from admin import render_admin_panel
from auth import authenticate, has_permission, get_role_label
from audit import (log_action,
                   ACTION_LOGIN, ACTION_LOGOUT, ACTION_LOGIN_FAILED,
                   ACTION_UPLOAD, ACTION_ANALYSIS_RUN, ACTION_SIM_RUN,
                   ACTION_ACCESS_DENIED,
                   STATUS_SUCCESS, STATUS_FAILED)

# ─────────────────────────────────────────────
# Page Config & Global CSS
# ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Natuna GPS Spoofing Detection",
    page_icon="🛰️"
)

st.markdown("""
<style>
.stApp { background: #0a0a1a; color: #e0e0ff; }
[data-testid="stSidebar"] { background: #0f0f2a; border-right: 1px solid #1e1e4a; }

.metric-card {
    background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
    border: 1px solid #2a2a5e; border-radius: 10px;
    padding: 14px 16px; margin-bottom: 8px;
}
.metric-label { color: #8888aa; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
.metric-value { color: #e0e0ff; font-size: 20px; font-weight: bold; }

@keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0.3; } }
.live-dot {
    display:inline-block; width:10px; height:10px;
    background:#ff4444; border-radius:50%;
    animation: blink 1s infinite; margin-right: 6px;
}

@keyframes pulse-border {
  0%,100% { box-shadow: 0 0 8px rgba(255,50,50,0.4); }
  50%      { box-shadow: 0 0 20px rgba(255,50,50,0.9); }
}

/* Login page */
.login-box {
    background: linear-gradient(135deg, #0f0f2b, #1a1a4a);
    border: 1px solid #2a2a6a; border-radius: 16px;
    padding: 40px; max-width: 420px; margin: auto;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Login Page
# ─────────────────────────────────────────────
def render_login_page():
    """Render centered login form. Returns nothing — handles auth via session_state."""
    st.markdown("<br><br>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
        <div style="text-align:center; margin-bottom:28px;">
          <div style="font-size:48px;">🛰️</div>
          <div style="color:#00BFFF;font-size:22px;font-weight:bold;margin-top:8px;">
            Natuna GPS Spoofing Detection
          </div>
          <div style="color:#666;font-size:13px;margin-top:4px;">
            Maritime Anomaly Detection System
          </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("#### 🔐 Login")
            username = st.text_input("Username", placeholder="Masukkan username...")
            password = st.text_input("Password", type="password", placeholder="Masukkan password...")
            submitted = st.form_submit_button("Login →", type="primary", use_container_width=True)

        if submitted:
            if not username or not password:
                st.warning("Username dan password wajib diisi.")
                return

            user = authenticate(username, password)
            if user:
                st.session_state['authenticated'] = True
                st.session_state['user'] = user
                log_action(user['id'], user['username'], ACTION_LOGIN, STATUS_SUCCESS,
                           f"Role: {user['role']}")
                st.rerun()
            else:
                log_action(0, username, ACTION_LOGIN_FAILED, STATUS_FAILED,
                           "Invalid username or password")
                st.error("❌ Username atau password salah.")

        st.markdown("""
        <div style="text-align:center; margin-top:20px; color:#555; font-size:12px;">
          Default: admin/admin123 · analyst/analyst123 · user/user123
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Core Processing Pipeline
# ─────────────────────────────────────────────
def process_row(row_dict: dict, previous_data: dict | None) -> dict:
    analyzed = analyze_vessel_data(row_dict, previous_data)
    risk_score, risk_level, spoofing = calculate_risk(
        analyzed['speed_alert'], analyzed['course_alert'],
        analyzed['geofence_alert'], analyzed['border_alert']
    )
    analyzed['risk_score']       = risk_score
    analyzed['risk_level']       = risk_level
    analyzed['spoofing_detected'] = spoofing
    return analyzed


# ─────────────────────────────────────────────
# Live Animation
# ─────────────────────────────────────────────
def run_live_animation(df: pd.DataFrame, source_label: str, interval: float, user: dict):
    user_id  = user['id']
    username = user['username']
    run_id   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{username}"
    total    = len(df)

    clear_data(user_id=user_id)

    log_action(user_id, username, ACTION_ANALYSIS_RUN, STATUS_SUCCESS,
               f"Started live analysis: {source_label} | {total} rows | run_id={run_id}")

    history       = []
    previous_data = None

    # Top banner
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,#0d0d2b,#1a1a4a);
                border:1px solid #2a2a6a;border-radius:10px;
                padding:12px 20px;margin-bottom:16px;">
      <span class="live-dot"></span>
      <span style="color:#00BFFF;font-size:18px;font-weight:bold;">LIVE VESSEL TRACKING</span>
      <span style="color:#888;font-size:12px;margin-left:12px;">
        Source: {source_label} | {total} pts | interval {interval}s | analyst: {username}
      </span>
    </div>""", unsafe_allow_html=True)

    col_left, col_map, col_right = st.columns([1, 2.2, 1], gap="small")

    with col_left:
        st.markdown("#### 📍 Current Position")
        ph_lat   = st.empty(); ph_lon  = st.empty()
        ph_spd   = st.empty(); ph_cog  = st.empty()
        ph_dist  = st.empty(); ph_fence = st.empty()
        st.divider()
        st.markdown("#### 📋 Alert Status")
        ph_speed_a  = st.empty(); ph_course_a = st.empty()
        ph_geo_a    = st.empty(); ph_border_a = st.empty()

    with col_map:
        st.markdown("#### 🗺️ Live Navigation Map")
        ph_map = st.empty()

    with col_right:
        st.markdown("#### 🎯 Risk Meter")
        ph_gauge     = st.empty()
        ph_risk_lvl  = st.empty()
        ph_spoofing  = st.empty()

    ph_progress = st.progress(0, text="Menunggu data pertama...")
    ph_step_log = st.empty()

    def badge(label, triggered, icon_on, icon_off):
        if triggered:
            return (f'<div style="background:#3a0000;border:1px solid #ff3333;'
                    f'border-radius:6px;padding:6px 10px;margin-bottom:6px;'
                    f'color:#ff6666;font-size:12px;">{icon_on} <b>{label}</b> — TRIGGERED</div>')
        return (f'<div style="background:#0a1a0a;border:1px solid #1a4a1a;'
                f'border-radius:6px;padding:6px 10px;margin-bottom:6px;'
                f'color:#448844;font-size:12px;">{icon_off} {label} — Clear</div>')

    def metric(label, val):
        return (f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{val}</div></div>')

    risk_colors = {'NORMAL':'#00CC66','LOW RISK':'#FFD700',
                   'MEDIUM RISK':'#FF8C00','HIGH RISK':'#FF3333'}

    for idx, row in df.iterrows():
        step     = int(idx) + 1
        analyzed = process_row(row.to_dict(), previous_data)

        # Inject user_id & run_id before DB insert
        analyzed['user_id'] = user_id
        analyzed['run_id']  = run_id
        insert_vessel_data(analyzed)

        if analyzed['spoofing_detected']:
            alerts = []
            if analyzed['speed_alert']:    alerts.append("Speed Anomaly")
            if analyzed['course_alert']:   alerts.append("Course Anomaly")
            if analyzed['geofence_alert']: alerts.append("Geofence Violation")
            if analyzed['border_alert']:   alerts.append("Border Proximity")
            insert_log(str(analyzed['timestamp']), "SPOOFING_DETECTED", "HIGH",
                       f"[{source_label}] Step {step} — " + ", ".join(alerts),
                       analyzed['risk_score'], user_id=user_id)

        history.append(analyzed)

        # Update metrics
        ph_lat.markdown(metric("Latitude",  f"{analyzed['latitude']:.5f}°"),  unsafe_allow_html=True)
        ph_lon.markdown(metric("Longitude", f"{analyzed['longitude']:.5f}°"), unsafe_allow_html=True)
        ph_spd.markdown(metric("Speed (SOG)",  f"{analyzed['speed']:.2f} knots"), unsafe_allow_html=True)
        ph_cog.markdown(metric("Course (COG)", f"{analyzed['course']:.1f}°"),     unsafe_allow_html=True)
        ph_dist.markdown(metric("Dist. to Border", f"{analyzed['distance_to_border']:.2f} km"), unsafe_allow_html=True)

        fc = "#00CC66" if analyzed['inside_geofence'] else "#FF4444"
        fv = "✅ Inside Zone" if analyzed['inside_geofence'] else "❌ Outside Zone"
        ph_fence.markdown(
            f'<div style="border:1px solid {fc};border-radius:6px;padding:8px;'
            f'text-align:center;color:{fc};font-weight:bold;font-size:13px;">🗺️ {fv}</div>',
            unsafe_allow_html=True)

        ph_speed_a.markdown(badge("Speed Check",         analyzed['speed_alert'],    "⚡","✅"), unsafe_allow_html=True)
        ph_course_a.markdown(badge("Course (ROT) Check", analyzed['course_alert'],   "🔄","✅"), unsafe_allow_html=True)
        ph_geo_a.markdown(badge("Geofence Check",        analyzed['geofence_alert'], "🚧","✅"), unsafe_allow_html=True)
        ph_border_a.markdown(badge("Border Proximity",   analyzed['border_alert'],   "🌐","✅"), unsafe_allow_html=True)

        with ph_map:
            from streamlit_folium import st_folium
            st_folium(build_live_map(history, analyzed), width=None, height=480, returned_objects=[])

        with ph_gauge:
            st.plotly_chart(build_gauge(analyzed['risk_score']),
                            use_container_width=True, key=f"gauge_{step}")

        rc = risk_colors.get(analyzed['risk_level'], '#888')
        ph_risk_lvl.markdown(
            f'<div style="text-align:center;padding:8px;border-radius:8px;'
            f'border:2px solid {rc};background:rgba(0,0,0,0.3);">'
            f'<span style="color:{rc};font-size:15px;font-weight:bold;">'
            f'{analyzed["risk_level"]}</span></div>', unsafe_allow_html=True)

        with ph_spoofing:
            if analyzed['spoofing_detected']:
                reasons = []
                if analyzed['speed_alert']:    reasons.append("⚡ Speed Anomaly")
                if analyzed['course_alert']:   reasons.append("🔄 Course Anomaly")
                if analyzed['geofence_alert']: reasons.append("🚧 Geofence Violation")
                if analyzed['border_alert']:   reasons.append("🌐 Border Proximity")
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#3a0000,#1a0000);'
                    f'border:2px solid #ff3333;border-radius:10px;padding:12px;'
                    f'text-align:center;box-shadow:0 0 20px rgba(255,50,50,0.5);">'
                    f'<div style="color:#FF3333;font-size:16px;font-weight:bold;">🚨 GPS SPOOFING DETECTED</div>'
                    f'<div style="color:#ff9999;font-size:12px;margin-top:8px;">{"<br>".join(reasons)}</div>'
                    f'</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="text-align:center;padding:10px;border-radius:8px;'
                    'border:1px solid #00CC66;background:rgba(0,80,0,0.1);">'
                    '<span style="color:#00CC66;font-size:12px;">✅ No Spoofing</span></div>',
                    unsafe_allow_html=True)

        pct = int((step / total) * 100)
        ph_progress.progress(pct, text=f"🔄 Step {step}/{total} — {analyzed['timestamp']}")

        with ph_step_log:
            sc = sum(1 for h in history if h.get('spoofing_detected'))
            ac = sum(1 for h in history if h.get('risk_score', 0) > 0)
            st.markdown(
                f'<div style="background:#0f0f23;border:1px solid #2a2a5e;'
                f'border-radius:8px;padding:8px 16px;font-size:12px;'
                f'color:#888;text-align:center;">'
                f'Steps: <b style="color:#00BFFF">{step}</b> &nbsp;|&nbsp;'
                f'Alerts: <b style="color:#FFA500">{ac}</b> &nbsp;|&nbsp;'
                f'Spoofing: <b style="color:#FF3333">{sc}</b></div>',
                unsafe_allow_html=True)

        previous_data = analyzed
        time.sleep(interval)

    spoofed_total = sum(1 for h in history if h.get('spoofing_detected'))
    st.markdown(
        f'<div style="background:linear-gradient(90deg,#0d2b0d,#1a4a1a);'
        f'border:1px solid #00CC66;border-radius:10px;'
        f'padding:14px 20px;text-align:center;margin-top:12px;">'
        f'<span style="color:#00FF88;font-size:16px;font-weight:bold;">'
        f'✅ Analisis Selesai — {total} titik diproses, {spoofed_total} spoofing terdeteksi'
        f'</span></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Batch Processing (Simulation)
# ─────────────────────────────────────────────
def process_dataframe_batch(df: pd.DataFrame, source_label: str, user: dict):
    user_id  = user['id']
    username = user['username']
    run_id   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{username}"
    total    = len(df)

    clear_data(user_id=user_id)
    log_action(user_id, username, ACTION_SIM_RUN, STATUS_SUCCESS,
               f"Simulation: {source_label} | {total} rows")

    previous_data  = None
    spoofing_count = 0
    progress_bar   = st.progress(0, text="Memulai analisis...")

    for i, row in df.iterrows():
        analyzed = process_row(row.to_dict(), previous_data)
        analyzed['user_id'] = user_id
        analyzed['run_id']  = run_id
        insert_vessel_data(analyzed)

        if analyzed['spoofing_detected']:
            spoofing_count += 1
            alerts = []
            if analyzed['speed_alert']:    alerts.append("Speed Anomaly")
            if analyzed['course_alert']:   alerts.append("Course Anomaly")
            if analyzed['geofence_alert']: alerts.append("Geofence Violation")
            if analyzed['border_alert']:   alerts.append("Border Proximity")
            insert_log(str(analyzed['timestamp']), "SPOOFING_DETECTED", "HIGH",
                       f"[{source_label}] " + ", ".join(alerts),
                       analyzed['risk_score'], user_id=user_id)

        previous_data = analyzed
        if int(i) % 5 == 0 or int(i) == total - 1:
            progress_bar.progress(int(((int(i)+1) / total) * 100),
                                  text=f"Menganalisis... {int(i)+1}/{total}")

    progress_bar.progress(100, text="✅ Selesai!")
    return spoofing_count


def run_simulation(simulation_type: str, user: dict):
    scenario_map = {
        "Normal Route":            generate_normal_route,
        "Sudden Jump Attack":      generate_sudden_jump_attack,
        "Slow-Onset Drift Attack": generate_slow_drift_attack,
        "Geofence Escape Attack":  generate_geofence_escape,
    }
    filepath = scenario_map[simulation_type]()
    df = load_dataset(filepath)
    if df.empty:
        st.error("Gagal memuat dataset simulasi.")
        return
    cnt = process_dataframe_batch(df, source_label=simulation_type, user=user)
    st.success(f"Simulasi selesai — {len(df)} titik, {cnt} anomali terdeteksi.")


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
def render_sidebar(user: dict) -> str:
    role     = user['role']
    username = user['username']

    st.sidebar.markdown(f"""
    <div style="text-align:center;padding:10px 0 4px;">
      <div style="font-size:26px;">🛰️</div>
      <div style="color:#00BFFF;font-size:14px;font-weight:bold;">Natuna GPS Spoofing</div>
      <div style="color:#888;font-size:11px;">Maritime Anomaly Detection</div>
    </div>
    <div style="background:#1a1a3e;border:1px solid #2a2a5e;border-radius:8px;
         padding:8px 12px;margin:8px 0;text-align:center;">
      <span style="color:#aaa;font-size:11px;">Logged in as</span><br>
      <span style="color:#00BFFF;font-weight:bold;">{username}</span>
      <span style="color:#888;font-size:11px;margin-left:6px;">{get_role_label(role)}</span>
    </div>
    """, unsafe_allow_html=True)

    # Navigation options based on role
    pages = ["🗺️ Dashboard", "📊 Report"]
    if has_permission(user, 'admin'):
        pages.append("🔧 Admin Panel")

    page = st.sidebar.radio("Navigasi", pages, label_visibility="collapsed")

    st.sidebar.divider()

    # Upload — Analyst + Admin only
    if has_permission(user, 'analyst'):
        st.sidebar.markdown("#### 📂 Upload Data Kapal")
        st.sidebar.caption("Format: `.csv` atau `.xlsx`\nKolom: `timestamp, latitude, longitude, sog, cog`")

        uploaded_file = st.sidebar.file_uploader(
            "Pilih file GPS", type=["csv", "xlsx", "xls"], key="file_uploader"
        )

        if uploaded_file is not None:
            df_upload, is_valid, missing_cols, error_msg = load_from_upload(uploaded_file)

            if error_msg:
                st.sidebar.error(f"❌ {error_msg}")
            elif not is_valid:
                st.sidebar.error("❌ Kolom tidak lengkap:")
                for col in missing_cols:
                    st.sidebar.code(col)
            else:
                n = len(df_upload)
                st.sidebar.success(f"✅ File valid — **{n} baris**")
                log_action(user['id'], username, ACTION_UPLOAD, STATUS_SUCCESS,
                           f"File: {uploaded_file.name} | {n} rows")

                with st.sidebar.expander("🔍 Preview"):
                    st.dataframe(
                        df_upload[['timestamp','latitude','longitude','sog','cog']].head(5),
                        use_container_width=True)

                interval = st.sidebar.slider(
                    "⏱️ Interval animasi (detik)", 0.2, 3.0, 1.0, 0.1
                )

                if st.sidebar.button("🚀 Mulai Analisis Live", type="primary", use_container_width=True):
                    fname = uploaded_file.name.rsplit('.', 1)[0]
                    st.session_state['animation_running']  = True
                    st.session_state['animation_df']       = df_upload
                    st.session_state['animation_label']    = fname
                    st.session_state['animation_interval'] = interval
                    st.rerun()

        st.sidebar.divider()

    # Simulation — Analyst + Admin only
    if has_permission(user, 'analyst'):
        st.sidebar.markdown("#### 🧪 Mode Simulasi")
        sim_type = st.sidebar.selectbox(
            "Pilih Skenario",
            ["Normal Route","Sudden Jump Attack","Slow-Onset Drift Attack","Geofence Escape Attack"],
            label_visibility="collapsed"
        )
        if st.sidebar.button("▶ Jalankan Simulasi", use_container_width=True):
            with st.spinner(f"Menjalankan: {sim_type}..."):
                run_simulation(sim_type, user)
            st.rerun()

        st.sidebar.divider()
    else:
        st.sidebar.info("ℹ️ Upload & simulasi hanya tersedia untuk Analyst dan Admin.")
        st.sidebar.divider()

    # Logout
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        log_action(user['id'], username, ACTION_LOGOUT, STATUS_SUCCESS)
        for key in ['authenticated','user','animation_running',
                    'animation_df','animation_label','animation_interval']:
            st.session_state.pop(key, None)
        st.rerun()

    return page


# ─────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────
def main():
    init_db()

    # ── AUTHENTICATION GATE ─────────────────────────────────
    # Must be first — st.stop() prevents any content rendering if not logged in
    if not st.session_state.get('authenticated'):
        render_login_page()
        st.stop()
        return

    user = st.session_state['user']

    # ── Sidebar (role-aware) ─────────────────────────────────
    page = render_sidebar(user)

    # ── Main Content Area ────────────────────────────────────
    if st.session_state.get('animation_running'):
        df_anim  = st.session_state.pop('animation_df')
        label    = st.session_state.pop('animation_label', 'Upload')
        interval = st.session_state.pop('animation_interval', 1.0)
        st.session_state['animation_running'] = False
        run_live_animation(df_anim, label, interval, user)

    elif "Dashboard" in page:
        render_dashboard(user)

    elif "Report" in page:
        render_report(user)

    elif "Admin" in page:
        if has_permission(user, 'admin'):
            render_admin_panel(user)
        else:
            log_action(user['id'], user['username'], ACTION_ACCESS_DENIED, STATUS_FAILED,
                       "Attempted to access Admin Panel without admin role")
            st.error("🚫 Akses ditolak. Halaman ini hanya untuk Admin.")


if __name__ == "__main__":
    main()
