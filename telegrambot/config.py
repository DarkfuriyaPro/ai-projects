import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Environment Variables
# ---------------------------------------------------------------------------

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# LLM API (OpenRouter or any OpenAI-compatible provider)
LLM_API_KEY: str  = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL: str    = os.getenv("LLM_MODEL", "openai/gpt-3.5-turbo")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_config() -> None:
    """
    Raise a clear EnvironmentError on startup if any required variable is missing.
    Call this once at the top of main() before building the Telegram app.
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
    Return a safe, secret-free summary of the current config for logging.
    API keys are masked — only the first 6 characters are shown.
    """
    def mask(value: str) -> str:
        return value[:6] + "..." if len(value) > 6 else "***"

    return (
        f"TELEGRAM_BOT_TOKEN={mask(TELEGRAM_BOT_TOKEN)} | "
        f"LLM_BASE_URL={LLM_BASE_URL} | "
        f"LLM_MODEL={LLM_MODEL} | "
        f"LLM_API_KEY={mask(LLM_API_KEY)}"
    )
