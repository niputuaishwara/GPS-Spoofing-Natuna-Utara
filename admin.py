import streamlit as st
import pandas as pd
import datetime

from database import get_analysis_results
from auth import (create_user, toggle_user_active, update_user_role,
                  delete_user, change_password, get_role_label, get_all_users)
from audit import (log_action, get_audit_logs, get_failed_logins,
                   ACTION_USER_CREATE, ACTION_USER_EDIT, ACTION_USER_DELETE, STATUS_SUCCESS, STATUS_FAILED)


# ─────────────────────────────────────────────────────────────
# Admin Panel — Full System Management
# ─────────────────────────────────────────────────────────────

def render_admin_panel(user: dict):
    """Render the full admin management panel."""
    admin_id   = user['id']
    admin_name = user['username']

    st.markdown("## 🔧 Admin Panel")

    tab_users, tab_audit, tab_analysis, tab_security = st.tabs([
        "👥 User Management",
        "📋 Audit Logs",
        "📊 All Analysis Results",
        "🔐 Security Monitor"
    ])

    # ── Tab 1: User Management ───────────────────────────────
    with tab_users:
        _render_user_management(admin_id, admin_name)

    # ── Tab 2: Audit Logs ───────────────────────────────────
    with tab_audit:
        _render_audit_logs()

    # ── Tab 3: All Analysis Results ─────────────────────────
    with tab_analysis:
        _render_all_analysis_results()

    # ── Tab 4: Security Monitor ──────────────────────────────
    with tab_security:
        _render_security_monitor()


# ─────────────────────────────────────────────────────────────
# User Management Tab
# ─────────────────────────────────────────────────────────────

def _render_user_management(admin_id: int, admin_name: str):
    st.markdown("#### 👥 Daftar User")
    users = get_all_users()

    if users:
        users_df = pd.DataFrame(users)
        users_df['role_label'] = users_df['role'].map({
            'admin': '🔴 Admin', 'analyst': '🟡 Analyst', 'user': '🟢 User'
        })
        users_df['status'] = users_df['is_active'].map({1: '✅ Active', 0: '❌ Inactive'})
        st.dataframe(
            users_df[['id', 'username', 'role_label', 'status', 'created_at', 'last_login']],
            use_container_width=True,
            hide_index=True
        )

    st.divider()
    col_create, col_edit = st.columns(2)

    # ── Create New User ──
    with col_create:
        st.markdown("##### ➕ Buat User Baru")
        with st.form("create_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role     = st.selectbox("Role", ["user", "analyst", "admin"])
            if st.form_submit_button("Buat User", type="primary"):
                if new_username and new_password:
                    ok, msg = create_user(new_username, new_password, new_role)
                    if ok:
                        log_action(admin_id, admin_name, ACTION_USER_CREATE, STATUS_SUCCESS,
                                   f"Created user '{new_username}' role={new_role}")
                        st.success(msg)
                        st.rerun()
                    else:
                        log_action(admin_id, admin_name, ACTION_USER_CREATE, STATUS_FAILED, msg)
                        st.error(msg)
                else:
                    st.warning("Username dan password wajib diisi")

    # ── Edit / Manage User ──
    with col_edit:
        st.markdown("##### ✏️ Edit User")
        if users:
            user_options = {f"{u['username']} (ID:{u['id']})": u['id'] for u in users}
            selected_label = st.selectbox("Pilih User", list(user_options.keys()))
            selected_id    = user_options[selected_label]
            selected_user  = next(u for u in users if u['id'] == selected_id)

            action = st.radio("Aksi", ["Ganti Role", "Ganti Password", "Toggle Status", "Hapus User"])

            if action == "Ganti Role":
                new_r = st.selectbox("Role Baru", ["user", "analyst", "admin"],
                                     index=["user","analyst","admin"].index(selected_user['role']))
                if st.button("Simpan Role"):
                    if selected_id == admin_id:
                        st.warning("Tidak bisa mengubah role diri sendiri")
                    else:
                        ok, msg = update_user_role(selected_id, new_r)
                        if ok:
                            log_action(admin_id, admin_name, ACTION_USER_EDIT, STATUS_SUCCESS,
                                       f"Changed role of '{selected_user['username']}' to {new_r}")
                            st.success(msg)
                            st.rerun()

            elif action == "Ganti Password":
                new_pw = st.text_input("Password Baru", type="password", key="new_pw_admin")
                if st.button("Simpan Password"):
                    ok, msg = change_password(selected_id, new_pw)
                    if ok:
                        log_action(admin_id, admin_name, ACTION_USER_EDIT, STATUS_SUCCESS,
                                   f"Changed password for '{selected_user['username']}'")
                        st.success(msg)
                    else:
                        st.error(msg)

            elif action == "Toggle Status":
                current_status = bool(selected_user['is_active'])
                label = "Nonaktifkan" if current_status else "Aktifkan"
                if st.button(f"{label} User", type="secondary"):
                    if selected_id == admin_id:
                        st.warning("Tidak bisa menonaktifkan diri sendiri")
                    else:
                        toggle_user_active(selected_id, not current_status)
                        log_action(admin_id, admin_name, ACTION_USER_EDIT, STATUS_SUCCESS,
                                   f"{label} user '{selected_user['username']}'")
                        st.success(f"User '{selected_user['username']}' berhasil di-{label.lower()}")
                        st.rerun()

            elif action == "Hapus User":
                st.warning(f"⚠️ Hapus user '{selected_user['username']}'? Aksi ini permanen.")
                if st.button("🗑️ Hapus", type="secondary"):
                    if selected_id == admin_id:
                        st.error("Tidak bisa menghapus akun sendiri")
                    else:
                        delete_user(selected_id)
                        log_action(admin_id, admin_name, ACTION_USER_DELETE, STATUS_SUCCESS,
                                   f"Deleted user '{selected_user['username']}'")
                        st.success("User dihapus")
                        st.rerun()


# ─────────────────────────────────────────────────────────────
# Audit Logs Tab
# ─────────────────────────────────────────────────────────────

def _render_audit_logs():
    st.markdown("#### 📋 System Audit Logs")
    st.caption("Semua aktivitas pengguna tercatat di sini untuk keperluan STRIDE/Repudiation analysis.")

    limit = st.slider("Tampilkan", 50, 500, 200, step=50)
    logs = get_audit_logs(limit=limit)

    if not logs:
        st.info("Belum ada log.")
        return

    logs_df = pd.DataFrame(logs)

    # Color-code status
    def style_status(val):
        if val == 'SUCCESS': return 'color: #00CC66'
        if val == 'FAILED':  return 'color: #FF4444'
        return 'color: #FFA500'

    # Filter controls
    col1, col2 = st.columns(2)
    with col1:
        filter_user = st.text_input("Filter by username", "")
    with col2:
        filter_action = st.selectbox("Filter by action", ["All"] + sorted(logs_df['action'].unique().tolist()))

    filtered = logs_df.copy()
    if filter_user:
        filtered = filtered[filtered['username'].str.contains(filter_user, case=False)]
    if filter_action != "All":
        filtered = filtered[filtered['action'] == filter_action]

    st.dataframe(
        filtered[['id','timestamp','username','action','status','metadata']],
        use_container_width=True,
        hide_index=True
    )

    # Export audit logs
    csv = filtered.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Export Audit Logs (CSV)", csv, "audit_logs.csv", "text/csv")


# ─────────────────────────────────────────────────────────────
# All Analysis Results (Admin View)
# ─────────────────────────────────────────────────────────────

def _render_all_analysis_results():
    st.markdown("#### 📊 Semua Hasil Analisis (Semua Analyst)")
    results = get_analysis_results(user_id=None)

    if not results:
        st.info("Belum ada hasil analisis tersimpan.")
        return

    df = pd.DataFrame(results)
    cat_map = {
        'confirmed_spoof':  '🚨 Confirmed Spoof',
        'false_positive':   '⚠️ False Positive',
        'under_review':     '🔍 Under Review',
        'normal_activity':  '✅ Normal'
    }
    if 'category' in df.columns:
        df['category'] = df['category'].map(cat_map).fillna(df['category'])

    st.dataframe(df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Export All Results (CSV)", csv, "all_analysis_results.csv", "text/csv")


# ─────────────────────────────────────────────────────────────
# Security Monitor Tab
# ─────────────────────────────────────────────────────────────

def _render_security_monitor():
    st.markdown("#### 🔐 Security Monitor")
    st.caption("STRIDE Threat Surface — Failed login attempts & suspicious activity")

    failed = get_failed_logins(limit=50)
    if failed:
        st.error(f"⚠️ {len(failed)} percobaan login gagal terdeteksi")
        st.dataframe(pd.DataFrame(failed)[['timestamp','username','status','metadata']],
                     use_container_width=True, hide_index=True)
    else:
        st.success("✅ Tidak ada percobaan login gagal")

    st.divider()
    st.markdown("##### 🧱 Trust Boundary Summary")
    st.markdown("""
    | Zona | Deskripsi | Status |
    |------|-----------|--------|
    | 🌐 External (Browser) | User input, file upload | Untrusted |
    | 🖥️ Streamlit Frontend | Form, UI, session state | Semi-trusted |
    | ⚙️ Processing Engine | Detection, Risk Scoring | Trusted |
    | 🗄️ Database (SQLite) | vessel_data, audit_logs | Trusted |
    """)

    st.markdown("##### ⚔️ STRIDE Threat Surface")
    st.markdown("""
    | Threat | Vektor | Kontrol |
    |--------|--------|---------|
    | **S** Spoofing | Fake login attempt | SHA-256 auth + audit log |
    | **T** Tampering | Modified CSV upload | Schema validation + size limit |
    | **R** Repudiation | Deny performing action | Audit logs (audit_logs table) |
    | **I** Information Disclosure | Unauthorized data access | Role-based data scoping |
    | **D** Denial of Service | Large file / loop abuse | File size + row limit |
    | **E** Elevation of Privilege | analyst → admin access | Role hierarchy check |
    """)
