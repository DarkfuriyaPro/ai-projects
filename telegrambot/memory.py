import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Maximum number of messages to keep per user (user + assistant turns combined).
# Keeps the context window from growing unbounded and avoids high token costs.
MAX_HISTORY_LENGTH = 20

# ---------------------------------------------------------------------------
# In-Memory Store
# ---------------------------------------------------------------------------

# Structure: { user_id (int): [ {"role": str, "content": str}, ... ] }
_conversation_store: dict[int, list[dict]] = defaultdict(list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_history(user_id: int) -> list[dict]:
    """
    Return a copy of the full conversation history for a user.

    Args:
        user_id: Telegram user ID (unique per user).

    Returns:
        List of role/content message dicts, oldest first.
    """
    return list(_conversation_store[user_id])


def add_message(user_id: int, role: str, content: str) -> None:
    """
    Append a single message to a user's conversation history,
    then trim to MAX_HISTORY_LENGTH if needed.

    Args:
        user_id: Telegram user ID.
        role:    "user" or "assistant".
        content: The message text.
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"Invalid role '{role}'. Must be 'user' or 'assistant'.")

    _conversation_store[user_id].append({"role": role, "content": content})

    # Trim oldest messages if we exceed the limit.
    history = _conversation_store[user_id]
    if len(history) > MAX_HISTORY_LENGTH:
        excess = len(history) - MAX_HISTORY_LENGTH
        _conversation_store[user_id] = history[excess:]
        logger.debug(f"Trimmed {excess} old message(s) for user {user_id}.")


def pop_last_message(user_id: int) -> dict | None:
    """
    Remove and return the most recent message for a user.
    Used to roll back a user message when an LLM call fails.

    Args:
        user_id: Telegram user ID.

    Returns:
        The removed message dict, or None if history was empty.
    """
    if _conversation_store[user_id]:
        removed = _conversation_store[user_id].pop()
        logger.debug(f"Rolled back last message for user {user_id}: {removed['role']!r}")
        return removed
    return None


def reset_history(user_id: int) -> None:
    """
    Clear the entire conversation history for a user.

    Args:
        user_id: Telegram user ID.
    """
    _conversation_store[user_id] = []
    logger.info(f"Conversation history cleared for user {user_id}.")


def get_history_length(user_id: int) -> int:
    """Return the number of messages stored for a user."""
    return len(_conversation_store[user_id])