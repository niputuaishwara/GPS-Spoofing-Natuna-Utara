import sqlite3
import os
import datetime
from typing import Dict, Any, List, Optional

DB_PATH = "database/natuna_spoofing.db"


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    """Initialize all database tables and run migrations."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── TABLE: users (NEW) ──────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt          TEXT NOT NULL,
        role          TEXT NOT NULL DEFAULT 'user',
        is_active     INTEGER NOT NULL DEFAULT 1,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login    DATETIME
    )
    ''')

    # ── TABLE: audit_logs (NEW) ─────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_logs (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id   INTEGER NOT NULL DEFAULT 0,
        username  TEXT NOT NULL DEFAULT 'anonymous',
        action    TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        status    TEXT NOT NULL,
        metadata  TEXT
    )
    ''')

    # ── TABLE: analysis_results (NEW) ──────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_results (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        run_id          TEXT NOT NULL,
        dataset_name    TEXT,
        total_records   INTEGER,
        spoofing_count  INTEGER,
        avg_risk_score  REAL,
        max_risk_score  INTEGER,
        category        TEXT DEFAULT 'under_review',
        analyst_notes   TEXT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # ── TABLE: vessel_data ──────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vessel_data (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id            INTEGER DEFAULT 0,
        run_id             TEXT DEFAULT '',
        timestamp          DATETIME,
        latitude           REAL,
        longitude          REAL,
        speed              REAL,
        course             REAL,
        distance_travelled REAL,
        distance_to_border REAL,
        inside_geofence    BOOLEAN,
        risk_score         INTEGER,
        risk_level         TEXT,
        speed_alert        BOOLEAN,
        course_alert       BOOLEAN,
        geofence_alert     BOOLEAN,
        border_alert       BOOLEAN,
        spoofing_detected  BOOLEAN,
        created_at         DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # ── TABLE: system_logs ──────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_logs (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER DEFAULT 0,
        timestamp  DATETIME,
        event_type TEXT,
        severity   TEXT,
        description TEXT,
        risk_score INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # ── TABLE: simulation_runs ──────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS simulation_runs (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        run_name         TEXT,
        dataset_name     TEXT,
        total_records    INTEGER,
        normal_records   INTEGER,
        alert_records    INTEGER,
        average_risk_score REAL,
        created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()

    # ── MIGRATION: add missing columns to existing tables ───
    _migrate(cursor, conn)

    conn.commit()
    conn.close()

    # ── Seed default admin user if no users exist ──────────
    _seed_default_users()


def _migrate(cursor, conn):
    """Add new columns to existing tables without breaking old data."""
    # vessel_data migrations
    cursor.execute("PRAGMA table_info(vessel_data)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if 'user_id' not in existing_cols:
        cursor.execute("ALTER TABLE vessel_data ADD COLUMN user_id INTEGER DEFAULT 0")
    if 'run_id' not in existing_cols:
        cursor.execute("ALTER TABLE vessel_data ADD COLUMN run_id TEXT DEFAULT ''")

    # system_logs migrations
    cursor.execute("PRAGMA table_info(system_logs)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if 'user_id' not in existing_cols:
        cursor.execute("ALTER TABLE system_logs ADD COLUMN user_id INTEGER DEFAULT 0")


def _seed_default_users():
    """Create default admin and analyst accounts on first run."""
    from auth import create_user
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        create_user('admin',   'admin123',    'admin')
        create_user('analyst', 'analyst123',  'analyst')
        create_user('user',    'user123',     'user')
        print("[DB] Default users seeded: admin/admin123, analyst/analyst123, user/user123")


# ─────────────────────────────────────────────────────────────
# Vessel Data CRUD
# ─────────────────────────────────────────────────────────────

def insert_vessel_data(data: Dict[str, Any]) -> None:
    """Insert a processed vessel data record. user_id and run_id should be in data dict."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO vessel_data (
            user_id, run_id,
            timestamp, latitude, longitude, speed, course,
            distance_travelled, distance_to_border, inside_geofence,
            risk_score, risk_level, speed_alert, course_alert,
            geofence_alert, border_alert, spoofing_detected
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('user_id', 0), data.get('run_id', ''),
        data.get('timestamp'), data.get('latitude'), data.get('longitude'),
        data.get('speed'), data.get('course'), data.get('distance_travelled'),
        data.get('distance_to_border'), data.get('inside_geofence'),
        data.get('risk_score'), data.get('risk_level'), data.get('speed_alert'),
        data.get('course_alert'), data.get('geofence_alert'), data.get('border_alert'),
        data.get('spoofing_detected')
    ))
    conn.commit()
    conn.close()


def get_all_vessel_data(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve vessel data. If user_id given, returns only that user's data."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute(
            'SELECT * FROM vessel_data WHERE user_id = ? ORDER BY timestamp ASC',
            (user_id,)
        )
    else:
        cursor.execute('SELECT * FROM vessel_data ORDER BY timestamp ASC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def clear_data(user_id: Optional[int] = None) -> None:
    """
    Clear vessel data and system logs.
    If user_id given, only clears that user's data (safe for multi-user).
    If user_id is None, clears ALL data (admin only).
    """
    conn = get_connection()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute('DELETE FROM vessel_data WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM system_logs WHERE user_id = ?', (user_id,))
    else:
        cursor.execute('DELETE FROM vessel_data')
        cursor.execute('DELETE FROM system_logs')
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# System Logs
# ─────────────────────────────────────────────────────────────

def insert_log(
    timestamp: str,
    event_type: str,
    severity: str,
    description: str,
    risk_score: int,
    user_id: int = 0
) -> None:
    """Insert a system detection event log."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO system_logs (user_id, timestamp, event_type, severity, description, risk_score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, timestamp, event_type, severity, description, risk_score))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# Analysis Results (Analyst Annotations)
# ─────────────────────────────────────────────────────────────

def insert_analysis_result(data: Dict[str, Any]) -> int:
    """Save an analyst's annotated analysis result. Returns new record id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO analysis_results
            (user_id, run_id, dataset_name, total_records, spoofing_count,
             avg_risk_score, max_risk_score, category, analyst_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('user_id', 0), data.get('run_id', ''),
        data.get('dataset_name', ''), data.get('total_records', 0),
        data.get('spoofing_count', 0), data.get('avg_risk_score', 0.0),
        data.get('max_risk_score', 0), data.get('category', 'under_review'),
        data.get('analyst_notes', '')
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_analysis_results(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get analysis results. Admin sees all; analyst sees own."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute(
            'SELECT * FROM analysis_results WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        )
    else:
        cursor.execute('SELECT * FROM analysis_results ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_analysis_result(result_id: int, category: str, notes: str) -> bool:
    """Update the category and notes of an existing analysis result."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE analysis_results SET category = ?, analyst_notes = ? WHERE id = ?',
        (category, notes, result_id)
    )
    conn.commit()
    conn.close()
    return True
