"""
database/db.py

Handles all database operations for the Telegram AI bot.
Uses SQLite — a simple file-based database built into Python.
No installation needed. The database file is created automatically on first run.

Tables:
    users    — stores basic info about each Telegram user
    messages — stores the full conversation history per user
"""

import sqlite3
import logging
from datetime import datetime

from config import DATABASE_PATH, MAX_HISTORY_LENGTH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection Helper
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    Open and return a connection to the SQLite database.

    We set row_factory so rows come back as dictionaries,
    meaning you can do row["content"] instead of row[0].
    Much easier to read!
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


# ---------------------------------------------------------------------------
# Setup — creates tables if they don't exist yet
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create the database tables on first run.
    Safe to call every startup — it uses IF NOT EXISTS so it
    won't overwrite anything if the tables are already there.
    """
    conn = get_connection()

    try:
        cursor = conn.cursor()

        # --- users table ---
        # Stores one row per Telegram user we've seen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY,  -- Telegram user ID (unique)
                username   TEXT,                 -- @username (can be empty)
                first_name TEXT,                 -- user's first name
                created_at TEXT                  -- when they first used the bot
            )
        """)

        # --- messages table ---
        # Stores every message in every conversation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto ID
                user_id    INTEGER NOT NULL,                   -- links to users.id
                role       TEXT    NOT NULL,                   -- "user" or "assistant"
                content    TEXT    NOT NULL,                   -- the message text
                created_at TEXT    NOT NULL,                   -- timestamp
                FOREIGN KEY (user_id) REFERENCES users(id)    -- enforces the link
            )
        """)

        conn.commit()
        logger.info(f"Database ready at: {DATABASE_PATH}")

    except sqlite3.Error as e:
        logger.error(f"Failed to initialise database: {e}")
        raise

    finally:
        conn.close()  # always close the connection when done


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def save_user(user_id: int, username: str, first_name: str) -> None:
    """
    Save a new user to the database, or update their info if they exist.
    Called every time a user sends a message so info stays fresh.

    Args:
        user_id:    Telegram user ID
        username:   @username (may be empty string)
        first_name: user's display name
    """
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO users (id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username or "", first_name, datetime.utcnow().isoformat()))
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to save user {user_id}: {e}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

def save_message(user_id: int, role: str, content: str) -> None:
    """
    Save a single message to the database.

    Args:
        user_id: Telegram user ID
        role:    "user" or "assistant"
        content: the message text
    """
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO messages (user_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, role, content, datetime.utcnow().isoformat()))
        conn.commit()
        logger.debug(f"Saved {role} message for user {user_id}.")
    except sqlite3.Error as e:
        logger.error(f"Failed to save message for user {user_id}: {e}")
    finally:
        conn.close()


def get_history(user_id: int) -> list[dict]:
    """
    Retrieve the recent conversation history for a user.
    Returns the last MAX_HISTORY_LENGTH messages, oldest first,
    in the format the LLM expects: [{"role": ..., "content": ...}]

    Args:
        user_id: Telegram user ID

    Returns:
        List of message dicts ready to pass to the AI
    """
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT role, content
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, MAX_HISTORY_LENGTH))

        rows = cursor.fetchall()

        # Rows come back newest-first (DESC), so we reverse them
        # to get oldest-first order for the AI context
        messages = [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
        return messages

    except sqlite3.Error as e:
        logger.error(f"Failed to get history for user {user_id}: {e}")
        return []
    finally:
        conn.close()


def delete_last_message(user_id: int) -> None:
    """
    Remove the most recent message for a user.
    Used to roll back a user message when an LLM call fails,
    so the failed message doesn't get stuck in history.

    Args:
        user_id: Telegram user ID
    """
    conn = get_connection()
    try:
        conn.execute("""
            DELETE FROM messages
            WHERE id = (
                SELECT id FROM messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
            )
        """, (user_id,))
        conn.commit()
        logger.debug(f"Rolled back last message for user {user_id}.")
    except sqlite3.Error as e:
        logger.error(f"Failed to delete last message for user {user_id}: {e}")
    finally:
        conn.close()


def reset_history(user_id: int) -> int:
    """
    Delete all messages for a user (called by /reset command).

    Args:
        user_id: Telegram user ID

    Returns:
        Number of messages that were deleted
    """
    conn = get_connection()
    try:
        cursor = conn.execute("""
            DELETE FROM messages WHERE user_id = ?
        """, (user_id,))
        conn.commit()
        count = cursor.rowcount  # how many rows were deleted
        logger.info(f"Cleared {count} messages for user {user_id}.")
        return count
    except sqlite3.Error as e:
        logger.error(f"Failed to reset history for user {user_id}: {e}")
        return 0
    finally:
        conn.close()


def get_history_length(user_id: int) -> int:
    """
    Return how many messages are stored for a user.
    Used by /reset to tell the user how many messages were cleared.

    Args:
        user_id: Telegram user ID
    """
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT COUNT(*) FROM messages WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logger.error(f"Failed to count messages for user {user_id}: {e}")
        return 0
    finally:
        conn.close()
