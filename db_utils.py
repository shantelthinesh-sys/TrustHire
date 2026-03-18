from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime

DB_NAME = "trusthire.db"


def db_path() -> str:
    return os.path.join(os.path.dirname(__file__), DB_NAME)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db() -> None:
    conn = sqlite3.connect(db_path())
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_username TEXT NOT NULL,
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

    conn.commit()
    conn.close()


def seed_default_admin() -> None:
    init_db()
    conn = sqlite3.connect(db_path())
    cur = conn.cursor()

    cur.execute("SELECT username FROM admin_users WHERE username = ?", ("admin",))
    exists = cur.fetchone()
    if not exists:
        cur.execute(
            "INSERT INTO admin_users (username, password_hash, created_at) VALUES (?, ?, ?)",
            ("admin", hash_password("admin123"), datetime.utcnow().isoformat()),
        )

    conn.commit()
    conn.close()


def authenticate_admin(username: str, password: str) -> bool:
    init_db()
    conn = sqlite3.connect(db_path())
    cur = conn.cursor()
    cur.execute(
        "SELECT password_hash FROM admin_users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return False

    return row[0] == hash_password(password)


def save_interview_session(record: dict) -> int:
    init_db()
    conn = sqlite3.connect(db_path())
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO interview_sessions (
            candidate_username,
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.get("candidate_username", "unknown"),
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
            datetime.utcnow().isoformat(),
        ),
    )

    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(session_id)


def list_interview_sessions(limit: int = 100) -> list[dict]:
    init_db()
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, candidate_username, started_at, ended_at, status,
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
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
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
