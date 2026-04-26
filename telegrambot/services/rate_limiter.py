"""
services/rate_limiter.py

Limits how many messages a user can send within a time window.
This protects your API credits from being used up by spam.

How it works:
    - Each user gets their own message counter and a timestamp
    - When a message arrives, we check if the time window has passed
    - If yes  → reset the counter (fresh window starts)
    - If no   → increment the counter
    - If the counter exceeds the limit → block the message

All limits are configured in config.py / .env:
    RATE_LIMIT_MAX_MESSAGES   = 10  (messages allowed per window)
    RATE_LIMIT_WINDOW_SECONDS = 60  (window size in seconds)

Example with defaults:
    User can send 10 messages per 60 seconds.
    On the 11th message they get a "slow down" warning.
    After 60 seconds their counter resets automatically.
"""

import logging
from datetime import datetime, timedelta

from config import RATE_LIMIT_MAX_MESSAGES, RATE_LIMIT_WINDOW_SECONDS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory store for rate limit data
# ---------------------------------------------------------------------------
# Structure: { user_id: {"count": int, "window_start": datetime} }
#
# Why in-memory and not SQLite?
# Rate limit data is temporary — it resets every minute.
# There's no reason to write it to disk. RAM is perfect for this.
#
_rate_limit_store: dict[int, dict] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_rate_limited(user_id: int) -> bool:
    """
    Check if a user has exceeded their message limit.

    Call this before processing any message. If it returns True,
    send the user a warning and skip the AI call.

    Args:
        user_id: Telegram user ID

    Returns:
        True  → user is over the limit, block the message
        False → user is within the limit, allow the message
    """
    now = datetime.utcnow()

    # First message from this user — set up their record
    if user_id not in _rate_limit_store:
        _rate_limit_store[user_id] = {
            "count": 1,
            "window_start": now,
        }
        logger.debug(f"Rate limit: new window started for user {user_id}.")
        return False  # first message is always allowed

    record = _rate_limit_store[user_id]
    window_start = record["window_start"]
    window_duration = timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)

    # Check if the current time window has expired
    if now - window_start > window_duration:
        # Window expired — reset the counter and start fresh
        _rate_limit_store[user_id] = {
            "count": 1,
            "window_start": now,
        }
        logger.debug(f"Rate limit: window reset for user {user_id}.")
        return False  # allow the message

    # Still within the window — increment the counter
    record["count"] += 1
    current_count = record["count"]

    # Check if they've gone over the limit
    if current_count > RATE_LIMIT_MAX_MESSAGES:
        logger.warning(
            f"Rate limit exceeded for user {user_id}: "
            f"{current_count}/{RATE_LIMIT_MAX_MESSAGES} messages "
            f"in {RATE_LIMIT_WINDOW_SECONDS}s window."
        )
        return True  # block the message

    logger.debug(
        f"Rate limit: user {user_id} at "
        f"{current_count}/{RATE_LIMIT_MAX_MESSAGES} messages."
    )
    return False  # allow the message


def get_seconds_until_reset(user_id: int) -> int:
    """
    Return how many seconds until a user's rate limit window resets.
    Used to tell the user exactly how long to wait.

    Args:
        user_id: Telegram user ID

    Returns:
        Seconds remaining in the current window, or 0 if no record exists.
    """
    if user_id not in _rate_limit_store:
        return 0

    now = datetime.utcnow()
    window_start = _rate_limit_store[user_id]["window_start"]
    window_duration = timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    elapsed = now - window_start
    remaining = window_duration - elapsed

    # Return seconds remaining, minimum 0
    return max(0, int(remaining.total_seconds()))
