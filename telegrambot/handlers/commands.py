"""
handlers/commands.py

Handles all Telegram bot commands:
    /start — welcome message
    /help  — usage guide
    /reset — clear conversation history

Each function follows the same pattern:
    async def command_name(update, context) -> None

    - update  = the incoming message/event from Telegram
    - context = extra info provided by python-telegram-bot (rarely needed here)
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database.db import save_user, reset_history, get_history_length

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Greet the user and show available commands.
    Also saves the user to the database if it's their first time.
    """
    user = update.effective_user

    # Save user to database (safe to call every time — updates if already exists)
    save_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "there",
    )

    logger.info(f"User {user.id} (@{user.username}) triggered /start.")

    await update.message.reply_text(
        f"👋 Hello, {user.first_name}!\n\n"
        "I'm your AI-powered assistant. Just send me a message and I'll reply "
        "using an advanced language model.\n\n"
        "📌 *Available commands:*\n"
        "/start — Show this welcome message\n"
        "/help  — Get help and usage tips\n"
        "/reset — Clear your conversation history\n\n"
        "Go ahead — say something! 🚀",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show a detailed usage guide with tips and example prompts.
    """
    user = update.effective_user
    logger.info(f"User {user.id} triggered /help.")

    await update.message.reply_text(
        "🤖 *AI Assistant — Help*\n\n"
        "*How to use:*\n"
        "Just type any message and I'll respond using AI. "
        "I remember your conversation so you can ask follow-up questions "
        "naturally — no need to repeat yourself.\n\n"
        "*Commands:*\n"
        "/start — Welcome message\n"
        "/help  — Show this help guide\n"
        "/reset — Wipe your conversation history and start fresh\n\n"
        "*Tips:*\n"
        "• Ask me anything — questions, coding help, writing, analysis\n"
        "• I remember your last 20 messages\n"
        "• If I seem confused, use /reset to start a clean session\n"
        "• Be specific — the more detail you give, the better my answers\n\n"
        "*Example prompts:*\n"
        "› \"Explain quantum computing in simple terms\"\n"
        "› \"Write a Python function to reverse a string\"\n"
        "› \"What are the pros and cons of remote work?\"\n\n"
        "💡 _Powered by OpenRouter · Built with python-telegram-bot_",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# /reset
# ---------------------------------------------------------------------------

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Clear the user's full conversation history from the database.
    Tells the user how many messages were deleted.
    """
    user = update.effective_user

    # Get count before deleting so we can report it to the user
    count = get_history_length(user.id)

    # Delete all messages for this user from SQLite
    reset_history(user.id)

    logger.info(f"User {user.id} reset conversation ({count} messages deleted).")

    if count == 0:
        await update.message.reply_text(
            "🗑 Your conversation history is already empty — nothing to clear!"
        )
    else:
        await update.message.reply_text(
            f"🗑 *Conversation reset.*\n\n"
            f"Cleared {count} message(s) from your history.\n"
            "Let's start fresh — what's on your mind?",
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# Unknown commands
# ---------------------------------------------------------------------------

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Catch any command the bot doesn't recognise (e.g. /foo).
    Must be registered LAST in main.py so it doesn't swallow valid commands.
    """
    await update.message.reply_text(
        "❓ Unknown command. Type /help to see what I can do."
    )
