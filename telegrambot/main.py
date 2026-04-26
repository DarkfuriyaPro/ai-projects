"""
main.py

Entry point for the Telegram AI Bot.
Run this file to start the bot:
    python main.py

This file only does four things:
    1. Validates configuration (.env variables)
    2. Initialises the database (creates tables if needed)
    3. Registers all handlers (commands + messages)
    4. Starts the bot and waits for messages

All the actual logic lives in:
    handlers/   — what happens when a message arrives
    services/   — AI calls and rate limiting
    database/   — saving and loading data
    config.py   — all settings
"""

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
from database.db import init_db
from handlers.commands import (
    start_command,
    help_command,
    reset_command,
    unknown_command,
)
from handlers.messages import handle_message


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
# This configures how log messages look throughout the entire project.
# Every file that does logger = logging.getLogger(__name__) uses this config.

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Catches any unexpected exception that slips through the handlers.
    Logs the full error and sends the user a polite message
    instead of the bot just going silent.
    """
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)

    # Only reply if this error happened inside a real user message
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "⚠️ Something went wrong on my end. Please try again in a moment."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Start the Telegram bot.

    Steps:
        1. Validate that all required .env variables are set
        2. Initialise the SQLite database
        3. Build the Telegram app
        4. Register all command and message handlers
        5. Start polling for new messages
    """

    # Step 1: Validate config — stop immediately if anything is missing
    validate_config()
    logger.info(f"Config OK — {debug_summary()}")

    # Step 2: Set up the database — creates tables on first run
    init_db()

    # Step 3: Build the Telegram application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Step 4: Register handlers
    # ORDER MATTERS — python-telegram-bot checks handlers top to bottom
    # and runs the first one that matches.

    # Commands — registered first so they always take priority
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(CommandHandler("reset", reset_command))

    # Plain text messages — only matches non-command messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Unknown commands — MUST be last or it catches everything
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Global error handler — catches anything the other handlers miss
    app.add_error_handler(error_handler)

    # Step 5: Start the bot
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
