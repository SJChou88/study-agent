import sqlite3
import os
from datetime import datetime, timezone

DB_FILE = os.path.join(os.path.dirname(__file__), "conversations.db")


def init_db() -> None:
    """Create the conversations table if it doesn't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT    NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                timestamp  TEXT    NOT NULL
            )
            """
        )


def save_turn(session_id: str, role: str, content: str) -> None:
    """Insert a single conversation turn into the database."""
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, role, content, timestamp),
        )


def get_session(session_id: str) -> list[dict]:
    """Return all turns for a session as a list of {role, content} dicts."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]


def list_sessions() -> list[dict]:
    """Return distinct sessions with their first user message and timestamp."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(
            """
            SELECT session_id, content, timestamp
            FROM conversations
            WHERE id IN (
                SELECT MIN(id)
                FROM conversations
                WHERE role = 'user'
                GROUP BY session_id
            )
            ORDER BY timestamp
            """
        )
        return [
            {"session_id": row[0], "first_message": row[1], "timestamp": row[2]}
            for row in cursor.fetchall()
        ]
