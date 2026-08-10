import hashlib
import os
import sqlite3
import datetime
from database import get_connection


# ─────────────────────────────────────────────────────────────
# Password Hashing — SHA-256 + Random Salt
# ─────────────────────────────────────────────────────────────

def hash_password(password: str) -> tuple[str, str]:
    """
    Hash a plain-text password using SHA-256 with a random salt.
    Returns: (hashed_password, salt)
    """
    salt = os.urandom(32).hex()  # 64-char hex string
    hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return hashed, salt


def verify_password(plain_password: str, hashed: str, salt: str) -> bool:
    """Verify a plain-text password against stored hash and salt."""
    computed = hashlib.sha256((plain_password + salt).encode('utf-8')).hexdigest()
    return computed == hashed


# ─────────────────────────────────────────────────────────────
# User Management
# ─────────────────────────────────────────────────────────────

def create_user(username: str, password: str, role: str = 'user') -> tuple[bool, str]:
    """
    Create a new user in the database.
    Returns: (success: bool, message: str)
    """
    if role not in ('admin', 'analyst', 'user'):
        return False, "Role tidak valid. Pilih: admin, analyst, user"
    if len(username.strip()) < 3:
        return False, "Username minimal 3 karakter"
    if len(password) < 6:
        return False, "Password minimal 6 karakter"

    hashed, salt = hash_password(password)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (username, password_hash, salt, role, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (username.strip().lower(), hashed, salt, role))
        conn.commit()
        return True, f"User '{username}' berhasil dibuat dengan role '{role}'"
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' sudah digunakan"
    finally:
        conn.close()


def authenticate(username: str, password: str) -> dict | None:
    """
    Authenticate a user by username and password.
    Returns user dict on success, None on failure.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, username, password_hash, salt, role, is_active FROM users WHERE username = ?',
        (username.strip().lower(),)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    user_id, uname, hashed, salt, role, is_active = row

    if not is_active:
        return None

    if not verify_password(password, hashed, salt):
        return None

    # Update last login timestamp
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET last_login = ? WHERE id = ?',
        (datetime.datetime.now().isoformat(), user_id)
    )
    conn.commit()
    conn.close()

    return {
        'id': user_id,
        'username': uname,
        'role': role
    }


def get_all_users() -> list[dict]:
    """Retrieve all users (for admin management)."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, username, role, is_active, created_at, last_login FROM users ORDER BY id ASC'
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def toggle_user_active(user_id: int, is_active: bool) -> bool:
    """Enable or disable a user account."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (1 if is_active else 0, user_id))
    conn.commit()
    conn.close()
    return True


def update_user_role(user_id: int, new_role: str) -> tuple[bool, str]:
    """Change a user's role."""
    if new_role not in ('admin', 'analyst', 'user'):
        return False, "Role tidak valid"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
    conn.commit()
    conn.close()
    return True, "Role berhasil diubah"


def delete_user(user_id: int) -> bool:
    """Delete a user (admin only, cannot delete self)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True


def change_password(user_id: int, new_password: str) -> tuple[bool, str]:
    """Change a user's password."""
    if len(new_password) < 6:
        return False, "Password minimal 6 karakter"
    hashed, salt = hash_password(new_password)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET password_hash = ?, salt = ? WHERE id = ?',
        (hashed, salt, user_id)
    )
    conn.commit()
    conn.close()
    return True, "Password berhasil diubah"


# ─────────────────────────────────────────────────────────────
# Session Helpers
# ─────────────────────────────────────────────────────────────

def get_role_label(role: str) -> str:
    """Return a human-readable role label with icon."""
    return {
        'admin':   '🔴 Admin',
        'analyst': '🟡 Analyst',
        'user':    '🟢 User',
    }.get(role, '⚪ Unknown')


def has_permission(user: dict, required_role: str) -> bool:
    """
    Check if a user has at least the required role level.
    Role hierarchy: admin > analyst > user
    """
    hierarchy = {'admin': 3, 'analyst': 2, 'user': 1}
    user_level = hierarchy.get(user.get('role', 'user'), 0)
    required_level = hierarchy.get(required_role, 99)
    return user_level >= required_level
