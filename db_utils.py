from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "trusthire.db"


def db_path() -> str:
    return os.path.join(os.path.dirname(__file__), DB_NAME)


def _utc_now() -> datetime:
    return datetime.utcnow()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols


def _ensure_column(cur: sqlite3.Cursor, table: str, column: str, dtype: str) -> None:
    if not _column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200000)
    return digest.hex()


def make_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{salt}${hash_password(password, salt)}"


def verify_password(password: str, stored_hash: str) -> bool:
    if "$" not in stored_hash:
        # Legacy hash fallback.
        return stored_hash == hashlib.sha256(password.encode("utf-8")).hexdigest()

    salt, digest = stored_hash.split("$", 1)
    return hash_password(password, salt) == digest


def init_db() -> None:
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_tokens (
            token TEXT PRIMARY KEY,
            candidate_username TEXT NOT NULL,
            recruiter_username TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            used_by TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_username TEXT NOT NULL,
            recruiter_username TEXT NOT NULL,
            scheduled_for TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 30,
            notes TEXT,
            token TEXT,
            status TEXT NOT NULL DEFAULT 'scheduled',
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_username TEXT NOT NULL,
            recruiter_username TEXT,
            interview_token TEXT,
            started_at TEXT,
            ended_at TEXT,
            status TEXT,
            policy_violations INTEGER DEFAULT 0,
            reading_alerts INTEGER DEFAULT 0,
            text_integrity_verdict TEXT,
            proctoring_integrity_score REAL DEFAULT 0,
            risk_label TEXT,
            terminated INTEGER DEFAULT 0,
            eye_away_ratio REAL DEFAULT 0,
            answers_json TEXT,
            violations_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    _ensure_column(cur, "interview_sessions", "recruiter_username", "TEXT")
    _ensure_column(cur, "interview_sessions", "interview_token", "TEXT")

    conn.commit()
    conn.close()


def seed_default_admin() -> None:
    seed_default_users()


def seed_default_users() -> None:
    init_db()
    conn = _connect()
    cur = conn.cursor()

    defaults = [
        ("admin", "admin123", "admin"),
        ("recruiter", "recruiter123", "recruiter"),
        ("candidate_demo", "demo123", "candidate"),
        ("trusthire_test", "pass2026", "candidate"),
    ]

    for username, password, role in defaults:
        cur.execute("SELECT username FROM users WHERE username = ?", (username,))
        exists = cur.fetchone()
        if not exists:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active, must_change_password, created_at)
                VALUES (?, ?, ?, 1, 0, ?)
                """,
                (username, make_password_hash(password), role, _utc_now().isoformat()),
            )

    conn.commit()
    conn.close()


def create_user(username: str, password: str, role: str, must_change_password: bool = True) -> tuple[bool, str]:
    init_db()
    username = (username or "").strip().lower()
    role = (role or "").strip().lower()
    if not username or not password:
        return False, "Username and password are required."
    if role not in {"admin", "recruiter", "candidate"}:
        return False, "Role must be admin, recruiter, or candidate."

    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT username FROM users WHERE username = ?",
        (username,)
    )
    exists = cur.fetchone()
    if exists:
        conn.close()
        return False, "Username already exists."

    cur.execute(
        """
        INSERT INTO users (username, password_hash, role, is_active, must_change_password, created_at)
        VALUES (?, ?, ?, 1, ?, ?)
        """,
        (
            username,
            make_password_hash(password),
            role,
            int(bool(must_change_password)),
            _utc_now().isoformat(),
        ),
    )

    conn.commit()
    conn.close()
    return True, "User created successfully."


def list_users(role: str | None = None) -> list[dict]:
    init_db()
    conn = _connect()
    cur = conn.cursor()

    if role:
        cur.execute(
            """
            SELECT username, role, is_active, must_change_password, created_at
            FROM users
            WHERE role = ?
            ORDER BY role, username
            """,
            (role,),
        )
    else:
        cur.execute(
            """
            SELECT username, role, is_active, must_change_password, created_at
            FROM users
            ORDER BY role, username
            """
        )

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def change_user_password(username: str, new_password: str, must_change_password: bool = False) -> bool:
    init_db()
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET password_hash = ?, must_change_password = ?
        WHERE username = ?
        """,
        (make_password_hash(new_password), int(bool(must_change_password)), username),
    )

    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def authenticate_user(username: str, password: str, allowed_roles: set[str] | None = None) -> bool:
    init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT password_hash, role, is_active FROM users WHERE username = ?",
        ((username or "").strip().lower(),),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return False
    if int(row["is_active"]) != 1:
        return False
    if allowed_roles and row["role"] not in allowed_roles:
        return False

    return verify_password(password, row["password_hash"])


def authenticate_admin(username: str, password: str) -> bool:
    return authenticate_user(username, password, allowed_roles={"admin"})


def create_interview_token(candidate_username: str, recruiter_username: str, valid_minutes: int = 30) -> tuple[bool, str, str]:
    init_db()
    token = "TH-" + secrets.token_hex(4).upper()
    now = _utc_now()
    expires_at = now + timedelta(minutes=max(5, valid_minutes))

    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT username FROM users WHERE username = ? AND role = 'candidate' AND is_active = 1",
        (candidate_username,),
    )
    if not cur.fetchone():
        conn.close()
        return False, "Candidate user not found or inactive.", ""

    cur.execute(
        """
        INSERT INTO interview_tokens (token, candidate_username, recruiter_username, status, created_at, expires_at)
        VALUES (?, ?, ?, 'issued', ?, ?)
        """,
        (token, candidate_username, recruiter_username, now.isoformat(), expires_at.isoformat()),
    )

    conn.commit()
    conn.close()
    return True, "Interview token created.", token


def list_interview_tokens(limit: int = 200) -> list[dict]:
    init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT token, candidate_username, recruiter_username, status, created_at, expires_at, used_at, used_by
        FROM interview_tokens
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def validate_candidate_login(candidate_username: str, password: str, token: str) -> tuple[bool, str]:
    if not authenticate_user(candidate_username, password, allowed_roles={"candidate"}):
        return False, "Invalid candidate credentials."

    init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT token, candidate_username, status, expires_at
        FROM interview_tokens
        WHERE token = ?
        """,
        ((token or "").strip(),),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return False, "Invalid interview token."
    if row["candidate_username"] != (candidate_username or "").strip().lower():
        return False, "Token not assigned to this candidate."
    if row["status"] != "issued":
        return False, "Interview token has already been used or invalidated."

    if datetime.fromisoformat(row["expires_at"]) < _utc_now():
        return False, "Interview token expired."

    return True, "Candidate login validated."


def mark_token_used(token: str, candidate_username: str) -> None:
    init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE interview_tokens
        SET status = 'used', used_at = ?, used_by = ?
        WHERE token = ?
        """,
        (_utc_now().isoformat(), candidate_username, token),
    )
    conn.commit()
    conn.close()


def create_schedule(
    candidate_username: str,
    recruiter_username: str,
    scheduled_for_iso: str,
    duration_minutes: int = 30,
    notes: str = "",
    token: str | None = None,
) -> tuple[bool, str, int]:
    init_db()
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT username FROM users WHERE username = ? AND role = 'candidate' AND is_active = 1",
        (candidate_username,),
    )
    if not cur.fetchone():
        conn.close()
        return False, "Candidate user not found or inactive.", 0

    cur.execute(
        """
        INSERT INTO interview_schedules (
            candidate_username,
            recruiter_username,
            scheduled_for,
            duration_minutes,
            notes,
            token,
            status,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'scheduled', ?)
        """,
        (
            candidate_username,
            recruiter_username,
            scheduled_for_iso,
            int(max(10, duration_minutes)),
            notes or "",
            token,
            _utc_now().isoformat(),
        ),
    )

    schedule_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return True, "Interview scheduled.", schedule_id


def list_schedules(limit: int = 200, status: str | None = None) -> list[dict]:
    init_db()
    conn = _connect()
    cur = conn.cursor()

    if status:
        cur.execute(
            """
            SELECT id, candidate_username, recruiter_username, scheduled_for, duration_minutes,
                   notes, token, status, created_at
            FROM interview_schedules
            WHERE status = ?
            ORDER BY scheduled_for ASC
            LIMIT ?
            """,
            (status, limit),
        )
    else:
        cur.execute(
            """
            SELECT id, candidate_username, recruiter_username, scheduled_for, duration_minutes,
                   notes, token, status, created_at
            FROM interview_schedules
            ORDER BY scheduled_for ASC
            LIMIT ?
            """,
            (limit,),
        )

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def set_schedule_status(schedule_id: int, status: str) -> bool:
    init_db()
    allowed = {"scheduled", "completed", "cancelled"}
    if status not in allowed:
        return False

    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE interview_schedules SET status = ? WHERE id = ?",
        (status, schedule_id),
    )
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def attach_token_to_schedule(schedule_id: int, token: str) -> bool:
    init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE interview_schedules SET token = ? WHERE id = ?",
        (token, schedule_id),
    )
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def save_interview_session(record: dict) -> int:
    init_db()
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO interview_sessions (
            candidate_username,
            recruiter_username,
            interview_token,
            started_at,
            ended_at,
            status,
            policy_violations,
            reading_alerts,
            text_integrity_verdict,
            proctoring_integrity_score,
            risk_label,
            terminated,
            eye_away_ratio,
            answers_json,
            violations_json,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.get("candidate_username", "unknown"),
            record.get("recruiter_username"),
            record.get("interview_token"),
            record.get("started_at"),
            record.get("ended_at"),
            record.get("status", "completed"),
            int(record.get("policy_violations", 0)),
            int(record.get("reading_alerts", 0)),
            record.get("text_integrity_verdict", ""),
            float(record.get("proctoring_integrity_score", 0.0)),
            record.get("risk_label", ""),
            int(bool(record.get("terminated", False))),
            float(record.get("eye_away_ratio", 0.0)),
            json.dumps(record.get("answers", []), ensure_ascii=True),
            json.dumps(record.get("violation_log", []), ensure_ascii=True),
            _utc_now().isoformat(),
        ),
    )

    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(session_id)


def list_interview_sessions(limit: int = 100) -> list[dict]:
    init_db()
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, candidate_username, recruiter_username, interview_token,
               started_at, ended_at, status,
               policy_violations, reading_alerts, text_integrity_verdict,
               proctoring_integrity_score, risk_label, terminated, eye_away_ratio, created_at
        FROM interview_sessions
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def get_interview_session(session_id: int) -> dict | None:
    init_db()
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM interview_sessions WHERE id = ?", (session_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    item = dict(row)
    item["answers_json"] = json.loads(item.get("answers_json") or "[]")
    item["violations_json"] = json.loads(item.get("violations_json") or "[]")
    return item


def dashboard_stats() -> dict:
    init_db()
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'candidate' AND is_active = 1")
    candidates = int(cur.fetchone()["n"])

    cur.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'recruiter' AND is_active = 1")
    recruiters = int(cur.fetchone()["n"])

    cur.execute("SELECT COUNT(*) AS n FROM interview_sessions")
    sessions = int(cur.fetchone()["n"])

    cur.execute(
        "SELECT COUNT(*) AS n FROM interview_sessions WHERE status = 'flagged' OR terminated = 1"
    )
    flagged = int(cur.fetchone()["n"])

    cur.execute("SELECT COUNT(*) AS n FROM interview_tokens WHERE status = 'issued'")
    active_tokens = int(cur.fetchone()["n"])

    cur.execute("SELECT COUNT(*) AS n FROM interview_schedules WHERE status = 'scheduled'")
    upcoming_schedules = int(cur.fetchone()["n"])

    conn.close()

    return {
        "active_candidates": candidates,
        "active_recruiters": recruiters,
        "sessions": sessions,
        "flagged_sessions": flagged,
        "active_tokens": active_tokens,
        "upcoming_schedules": upcoming_schedules,
    }
