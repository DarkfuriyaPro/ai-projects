import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, validate_config, debug_summary
from llm_client import get_llm_response
from memory import (
    add_message,
    get_history,
    get_history_length,
    pop_last_message,
    reset_history,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — greet the user."""
    user = update.effective_user
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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — explain features and usage."""
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
        "• I remember up to the last 20 messages in our conversation\n"
        "• If I seem confused, use /reset to start a clean session\n"
        "• Be specific — the more detail you give, the better my answers\n\n"
        "*Example prompts:*\n"
        "› \"Explain quantum computing in simple terms\"\n"
        "› \"Write a Python function to reverse a string\"\n"
        "› \"What are the pros and cons of remote work?\"\n\n"
        "💡 _Powered by OpenRouter · Built with python-telegram-bot_",
        parse_mode="Markdown",
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset — clear the user's conversation history."""
    user = update.effective_user
    count = get_history_length(user.id)
    reset_history(user.id)

    logger.info(f"User {user.id} reset conversation ({count} messages cleared).")

    if count == 0:
        await update.message.reply_text(
            "🗑 Your conversation history is already empty — nothing to clear!"
        )
    else:
        await update.message.reply_text(
            f"🗑 *Conversation reset.*\n\n"
            f"Cleared {count} message(s) from our history.\n"
            "Let's start fresh — what's on your mind?",
            parse_mode="Markdown",
        )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unrecognised commands."""
    await update.message.reply_text(
        "❓ Unknown command. Type /help to see what I can do."
    )


# ---------------------------------------------------------------------------
# Message Handler
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle plain text messages.

    Flow:
      1. Append the user message to memory.
      2. Send the full conversation history to the LLM.
      3. On success — append the reply to memory and send it.
      4. On failure — roll back the user message and show an error.
    """
    user = update.effective_user
    user_text = update.message.text.strip()

    if not user_text:
        return  # Ignore empty messages

    logger.info(f"Message from user {user.id}: {user_text[:80]!r}")

    # Immediate feedback while the LLM processes
    await update.message.chat.send_action(action="typing")

    # 1. Persist user message
    add_message(user_id=user.id, role="user", content=user_text)

    # 2. Build full context and call LLM
    try:
        reply = await get_llm_response(get_history(user.id))
    except RuntimeError as e:
        # 4. Roll back so the failed message isn't stuck in history
        pop_last_message(user.id)
        logger.warning(f"LLM error for user {user.id}: {e}")
        await update.message.reply_text(f"⚠️ {e}")
        return

    # 3. Persist assistant reply and respond
    add_message(user_id=user.id, role="assistant", content=reply)
    await update.message.reply_text(reply)


# ---------------------------------------------------------------------------
# Global Error Handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unexpected exceptions raised inside any handler."""
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)

    # Notify the user if the error occurred inside a real Update
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "⚠️ An unexpected error occurred. Please try again in a moment."
        )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    """Validate config, build the app, register handlers, and start polling."""
    validate_config()
    logger.info(f"Config loaded — {debug_summary()}")
    logger.info("Starting Telegram AI Bot...")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(CommandHandler("reset", reset_command))

    # Plain text messages (non-commands)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Catch-all for unknown commands — must be registered last
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Global error handler
    app.add_error_handler(error_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
