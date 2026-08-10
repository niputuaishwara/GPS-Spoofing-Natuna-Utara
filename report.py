import streamlit as st
import pandas as pd
import datetime
import sqlite3

from database import get_connection, get_analysis_results, update_analysis_result, get_all_vessel_data
from audit import log_action, ACTION_EXPORT, ACTION_REPORT_VIEW, ACTION_ANALYSIS_SAVE, STATUS_SUCCESS
from auth import has_permission


# ─────────────────────────────────────────────────────────────
# Report Page — Role-Aware
# ─────────────────────────────────────────────────────────────

def render_report(user: dict):
    """
    Render the report page.
    - Admin: sees all data from all users
    - Analyst: sees own data + can annotate analysis results
    - User: sees own data, read-only
    """
    user_id   = user['id']
    username  = user['username']
    role      = user['role']

    log_action(user_id, username, ACTION_REPORT_VIEW, STATUS_SUCCESS)

    st.markdown("## 📊 Detection Report")

    # ── Admin sees all data; others see own ──
    if has_permission(user, 'admin'):
        data = get_all_vessel_data(user_id=None)  # all users
        st.caption("🔴 Admin view — menampilkan seluruh data semua user")
    else:
        data = get_all_vessel_data(user_id=user_id)
        st.caption(f"Data milik: **{username}**")

    if not data:
        st.info("Belum ada data. Jalankan analisis atau simulasi terlebih dahulu.")
        _render_analysis_history(user, role, user_id, username)
        return

    df = pd.DataFrame(data)

    # ── Summary Metrics ──────────────────────────────────────
    total_data    = len(df)
    total_alert   = len(df[df['risk_score'] >= 50])
    avg_risk      = df['risk_score'].mean()
    high_risk     = df['risk_score'].max()
    detection_rate = (total_alert / total_data * 100) if total_data > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Data",            total_data)
    c2.metric("Spoofing Events",        total_alert)
    c3.metric("Avg Risk Score",         f"{avg_risk:.1f}")
    c4.metric("Max Risk Score",         high_risk)
    c5.metric("Detection Rate",         f"{detection_rate:.1f}%")

    st.divider()

    # ── Export (Analyst + Admin only) ────────────────────────
    if has_permission(user, 'analyst'):
        st.markdown("#### 📥 Export Data")
        col_a, col_b = st.columns(2)

        with col_a:
            csv_data = df.to_csv(index=False).encode('utf-8')
            if st.download_button(
                label="⬇️ Download CSV Report",
                data=csv_data,
                file_name=f"natuna_detection_{username}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime='text/csv'
            ):
                log_action(user_id, username, ACTION_EXPORT, STATUS_SUCCESS,
                           f"CSV export — {total_data} records")

        with col_b:
            report_text = _generate_text_report(df, username, total_data, total_alert, avg_risk, high_risk, detection_rate)
            if st.download_button(
                label="⬇️ Download Text Report",
                data=report_text.encode('utf-8'),
                file_name=f"natuna_report_{username}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime='text/plain'
            ):
                log_action(user_id, username, ACTION_EXPORT, STATUS_SUCCESS,
                           f"Text report export — {username}")

    st.divider()

    # ── Analyst Annotation Form ──────────────────────────────
    if has_permission(user, 'analyst'):
        _render_annotation_form(df, user_id, username)
        st.divider()

    # ── Analysis History ─────────────────────────────────────
    _render_analysis_history(user, role, user_id, username)

    st.divider()

    # ── Data Table ──────────────────────────────────────────
    st.markdown("#### 🗂️ Data Table")
    display_cols = ['timestamp','latitude','longitude','speed','course',
                    'risk_score','risk_level','speed_alert','course_alert',
                    'geofence_alert','border_alert','spoofing_detected']
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available], use_container_width=True)


# ─────────────────────────────────────────────────────────────
# Analyst Annotation Form
# ─────────────────────────────────────────────────────────────

def _render_annotation_form(df: pd.DataFrame, user_id: int, username: str):
    st.markdown("#### 📝 Analyst Annotation")
    st.caption("Simpan hasil analisis dan kategorikan temuan spoofing.")

    with st.form("annotation_form"):
        col1, col2 = st.columns([1, 2])
        with col1:
            category = st.selectbox(
                "Kategori Temuan",
                options=[
                    "confirmed_spoof",
                    "false_positive",
                    "under_review",
                    "normal_activity"
                ],
                format_func=lambda x: {
                    'confirmed_spoof':   '🚨 Confirmed GPS Spoofing',
                    'false_positive':    '⚠️ False Positive',
                    'under_review':      '🔍 Under Review',
                    'normal_activity':   '✅ Normal Activity'
                }.get(x, x)
            )
        with col2:
            notes = st.text_area(
                "Catatan Analyst",
                placeholder="Deskripsikan temuan, konteks serangan, rekomendasi tindak lanjut...",
                height=100
            )

        submitted = st.form_submit_button("💾 Simpan Hasil Analisis", type="primary")
        if submitted:
            from database import insert_analysis_result
            import uuid
            run_id = str(uuid.uuid4())[:8]

            spoofing_count = len(df[df['spoofing_detected'] == True]) if 'spoofing_detected' in df.columns else 0

            insert_analysis_result({
                'user_id':        user_id,
                'run_id':         run_id,
                'dataset_name':   f"session_{username}",
                'total_records':  len(df),
                'spoofing_count': spoofing_count,
                'avg_risk_score': float(df['risk_score'].mean()) if 'risk_score' in df.columns else 0,
                'max_risk_score': int(df['risk_score'].max()) if 'risk_score' in df.columns else 0,
                'category':       category,
                'analyst_notes':  notes
            })
            log_action(user_id, username, ACTION_ANALYSIS_SAVE, STATUS_SUCCESS,
                       f"Category: {category} | Notes: {notes[:50]}")
            st.success("✅ Hasil analisis berhasil disimpan!")
            st.rerun()


# ─────────────────────────────────────────────────────────────
# Analysis History Table
# ─────────────────────────────────────────────────────────────

def _render_analysis_history(user: dict, role: str, user_id: int, username: str):
    st.markdown("#### 📋 Riwayat Analisis")

    # Admin sees all; others see own
    if has_permission(user, 'admin'):
        results = get_analysis_results(user_id=None)
    else:
        results = get_analysis_results(user_id=user_id)

    if not results:
        st.info("Belum ada riwayat analisis tersimpan.")
        return

    results_df = pd.DataFrame(results)

    # Map category to label
    cat_map = {
        'confirmed_spoof':  '🚨 Confirmed Spoof',
        'false_positive':   '⚠️ False Positive',
        'under_review':     '🔍 Under Review',
        'normal_activity':  '✅ Normal'
    }
    if 'category' in results_df.columns:
        results_df['category'] = results_df['category'].map(cat_map).fillna(results_df['category'])

    st.dataframe(
        results_df[['id','created_at','dataset_name','total_records','spoofing_count',
                    'avg_risk_score','max_risk_score','category','analyst_notes']],
        use_container_width=True
    )


# ─────────────────────────────────────────────────────────────
# Text Report Generator
# ─────────────────────────────────────────────────────────────

def _generate_text_report(df, username, total, alerts, avg, max_r, rate) -> str:
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    spoofed_rows = df[df.get('spoofing_detected', False) == True] if 'spoofing_detected' in df.columns else pd.DataFrame()
    lines = [
        "=" * 60,
        "  NATUNA GPS SPOOFING DETECTION — ANALYSIS REPORT",
        "=" * 60,
        f"  Generated   : {ts}",
        f"  Analyst     : {username}",
        f"  System      : Natuna GPS Spoofing Detection Dashboard",
        "=" * 60,
        "",
        "[ SUMMARY ]",
        f"  Total Data Points   : {total}",
        f"  Spoofing Events     : {alerts}",
        f"  Average Risk Score  : {avg:.2f}",
        f"  Maximum Risk Score  : {max_r}",
        f"  Detection Rate      : {rate:.2f}%",
        "",
        "[ DETECTION METHODS ]",
        "  1. Speed Check         (threshold: >80 km/h)",
        "  2. Rate of Turn Check  (threshold: >45 deg/step)",
        "  3. Geofence Check      (Natuna Zone: 107-111E, 3-7N)",
        "  4. Border Proximity    (threshold: >5 km change/step)",
        "",
    ]
    if not spoofed_rows.empty:
        lines.append("[ SPOOFING EVENTS (first 10) ]")
        for _, row in spoofed_rows.head(10).iterrows():
            lines.append(
                f"  [{row.get('timestamp','')}] "
                f"Lat:{row.get('latitude','?'):.4f} "
                f"Lon:{row.get('longitude','?'):.4f} "
                f"Risk:{row.get('risk_score','?')} "
                f"Level:{row.get('risk_level','?')}"
            )
    lines += ["", "=" * 60, "  END OF REPORT", "=" * 60]
    return "\n".join(lines)
