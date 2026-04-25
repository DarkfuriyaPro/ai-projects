import os
from dotenv import load_dotenv

# Load variables from the .env file into the environment
load_dotenv()


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")


# ---------------------------------------------------------------------------
# LLM / AI Provider (OpenRouter or any OpenAI-compatible API)
# ---------------------------------------------------------------------------

LLM_API_KEY: str  = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL: str    = os.getenv("LLM_MODEL", "openai/gpt-3.5-turbo")

# How creative the AI responses are (0.0 = robotic, 1.0 = very creative)
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Maximum number of words (tokens) the AI can reply with
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1000"))

# How many seconds to wait for the AI before giving up
LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

# How many times to retry if the AI server has a temporary problem
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))

# The personality/instructions given to the AI at the start of every conversation
SYSTEM_PROMPT: str = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful, concise, and friendly AI assistant inside a Telegram bot. "
    "Keep your answers clear and to the point. "
    "If you don't know something, say so honestly. "
    "Use plain text only — no markdown, no asterisks, no special formatting, "
    "since this is a chat interface."
)


# ---------------------------------------------------------------------------
# Memory / Conversation History
# ---------------------------------------------------------------------------

# How many messages to remember per user (user + assistant messages combined)
# Example: 20 means the last 10 exchanges (10 user + 10 assistant)
MAX_HISTORY_LENGTH: int = int(os.getenv("MAX_HISTORY_LENGTH", "20"))


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

# Maximum number of messages a user can send per minute
RATE_LIMIT_MAX_MESSAGES: int = int(os.getenv("RATE_LIMIT_MAX_MESSAGES", "10"))

# The time window in seconds for the rate limit (default: 60 = 1 minute)
RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# Path to the SQLite database file (created automatically on first run)
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_database.db")


# ---------------------------------------------------------------------------
# Validation — runs once at startup
# ---------------------------------------------------------------------------

def validate_config() -> None:
    """
    Check that all required environment variables are set.
    If anything is missing, stop the bot immediately with a clear message.
    Call this once at the top of main.py before starting the bot.
    """
    missing = [
        name
        for name, value in [
            ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
            ("LLM_API_KEY", LLM_API_KEY),
        ]
        if not value
    ]

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please copy .env.example to .env and fill in your values."
        )


def debug_summary() -> str:
    """
    Returns a safe summary of the current config for logging on startup.
    API keys are masked so they never appear in log files.
    """
    def mask(value: str) -> str:
        return value[:6] + "..." if len(value) > 6 else "***"

    return (
        f"model={LLM_MODEL} | "
        f"temperature={LLM_TEMPERATURE} | "
        f"max_tokens={LLM_MAX_TOKENS} | "
        f"max_history={MAX_HISTORY_LENGTH} | "
        f"rate_limit={RATE_LIMIT_MAX_MESSAGES}/{RATE_LIMIT_WINDOW_SECONDS}s | "
        f"db={DATABASE_PATH} | "
        f"token={mask(TELEGRAM_BOT_TOKEN)} | "
        f"api_key={mask(LLM_API_KEY)}"
    )