"""
handlers/messages.py

Handles every regular text message a user sends (anything that isn't a command).

This is the core of the bot — it connects all the pieces:
    - rate_limiter  → checks if the user is sending too fast
    - database.db   → saves users and messages, loads history
    - ai_service    → sends history to the AI and gets a reply

Flow:
    1. Check rate limit       — protect API credits
    2. Save user to DB        — keep user records fresh
    3. Show typing indicator  — instant feedback for the user
    4. Save user message      — persist before calling AI
    5. Load full history      — give the AI full context
    6. Call the AI            — get the reply
    7. On failure             — roll back the saved message
    8. Save AI reply          — persist the response
    9. Send reply to user     — done!
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database.db import save_user, save_message, get_history, delete_last_message
from services.ai_service import get_ai_response
from services.rate_limiter import is_rate_limited, get_seconds_until_reset

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Process a plain text message from a user.

    This function is registered in main.py to handle all non-command messages.
    It runs every time a user types something that isn't /start, /help, or /reset.
    """
    user = update.effective_user
    user_text = update.message.text.strip()

    # Guard: ignore empty or whitespace-only messages
    if not user_text:
        return

    logger.info(f"Message from user {user.id} (@{user.username}): {user_text[:80]!r}")

    # ------------------------------------------------------------------
    # Step 1: Rate limiting
    # Check if the user is sending messages too fast.
    # If yes — warn them and stop here (don't call the AI).
    # ------------------------------------------------------------------
    if is_rate_limited(user.id):
        seconds_left = get_seconds_until_reset(user.id)
        logger.warning(f"Rate limit hit for user {user.id}. Reset in {seconds_left}s.")
        await update.message.reply_text(
            f"You're sending messages too fast.\n"
            f"Please wait {seconds_left} seconds and try again."
        )
        return

    # ------------------------------------------------------------------
    # Step 2: Save user info to the database
    # We do this on every message so their name/username stays up to date.
    # ------------------------------------------------------------------
    save_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
    )

    # ------------------------------------------------------------------
    # Step 3: Show typing indicator
    # This appears immediately so the user knows something is happening
    # while we wait for the AI to respond (can take 2-5 seconds).
    # ------------------------------------------------------------------
    await update.message.chat.send_action(action="typing")

    # ------------------------------------------------------------------
    # Step 4: Save the user's message to the database
    # We save it BEFORE calling the AI so it becomes part of the history.
    # If the AI call fails, we'll roll this back in Step 7.
    # ------------------------------------------------------------------
    save_message(user_id=user.id, role="user", content=user_text)

    # ------------------------------------------------------------------
    # Step 5: Load the full conversation history
    # This gives the AI context about what was said before,
    # so it can give relevant follow-up responses.
    # ------------------------------------------------------------------
    history = get_history(user_id=user.id)

    # ------------------------------------------------------------------
    # Step 6: Call the AI with the full history
    # ------------------------------------------------------------------
    try:
        reply = await get_ai_response(history)

    except RuntimeError as e:
        # ------------------------------------------------------------------
        # Step 7: Roll back on failure
        # The AI call failed — remove the user message we saved in Step 4
        # so it doesn't get stuck in the history and confuse future responses.
        # ------------------------------------------------------------------
        delete_last_message(user.id)
        logger.warning(f"AI error for user {user.id}: {e}")
        await update.message.reply_text(f"{e}")
        return

    # ------------------------------------------------------------------
    # Step 8: Save the AI's reply to the database
    # ------------------------------------------------------------------
    save_message(user_id=user.id, role="assistant", content=reply)

    # ------------------------------------------------------------------
    # Step 9: Send the reply to the user
    # ------------------------------------------------------------------
    await update.message.reply_text(reply)
