import datetime
import sqlite3
from database import get_connection


# ─────────────────────────────────────────────────────────────
# Audit Logging — Full Activity Tracking
# Supports STRIDE "Repudiation" analysis
# ─────────────────────────────────────────────────────────────

# Defined action types for consistent logging
ACTION_LOGIN         = "LOGIN"
ACTION_LOGOUT        = "LOGOUT"
ACTION_LOGIN_FAILED  = "LOGIN_FAILED"
ACTION_UPLOAD        = "DATASET_UPLOAD"
ACTION_ANALYSIS_RUN  = "ANALYSIS_RUN"
ACTION_SIM_RUN       = "SIMULATION_RUN"
ACTION_EXPORT        = "EXPORT"
ACTION_REPORT_VIEW   = "REPORT_VIEW"
ACTION_USER_CREATE   = "USER_CREATE"
ACTION_USER_EDIT     = "USER_EDIT"
ACTION_USER_DELETE   = "USER_DELETE"
ACTION_ACCESS_DENIED = "ACCESS_DENIED"
ACTION_ANALYSIS_SAVE = "ANALYSIS_SAVE"

STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED  = "FAILED"
STATUS_WARNING = "WARNING"


def log_action(
    user_id: int,
    username: str,
    action: str,
    status: str,
    metadata: str = ''
) -> None:
    """
    Insert an audit log entry into the database.

    Args:
        user_id:  ID of the acting user (0 for unauthenticated attempts)
        username: Username string (for readability even if user deleted later)
        action:   Action type constant (use ACTION_* constants above)
        status:   STATUS_SUCCESS / STATUS_FAILED / STATUS_WARNING
        metadata: Optional context (filename, dataset info, error message, etc.)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_logs (user_id, username, action, timestamp, status, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        username,
        action,
        datetime.datetime.now().isoformat(),
        status,
        metadata
    ))
    conn.commit()
    conn.close()


def get_audit_logs(limit: int = 500) -> list[dict]:
    """
    Retrieve recent audit log entries, newest first.
    Args:
        limit: Maximum number of records to return
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?',
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_user_audit_logs(user_id: int, limit: int = 100) -> list[dict]:
    """Retrieve audit logs for a specific user."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM audit_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_failed_logins(limit: int = 50) -> list[dict]:
    """Retrieve failed login attempts for security monitoring."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT * FROM audit_logs
           WHERE action = ? AND status = ?
           ORDER BY timestamp DESC LIMIT ?''',
        (ACTION_LOGIN_FAILED, STATUS_FAILED, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
