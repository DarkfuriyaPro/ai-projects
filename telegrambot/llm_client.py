import logging
import httpx

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIMEOUT_SECONDS = 30
MAX_TOKENS = 1000
MAX_RETRIES = 2  # Number of retry attempts on transient failures

# System prompt — defines the assistant's personality and behaviour
SYSTEM_PROMPT = (
    "You are a helpful, concise, and friendly AI assistant inside a Telegram bot. "
    "Keep your answers clear and to the point. "
    "If you don't know something, say so honestly. "
    "Use plain text only — no markdown, no asterisks, no special formatting, "
    "since this is a chat interface."
)


# ---------------------------------------------------------------------------
# Core LLM call
# ---------------------------------------------------------------------------

async def get_llm_response(messages: list[dict]) -> str:
    """
    Send a conversation history to the LLM and return the assistant's reply.
    Retries up to MAX_RETRIES times on transient network or server errors.

    Args:
        messages: A list of role/content dicts representing the conversation.
                  e.g. [{"role": "user", "content": "Hello!"}]

    Returns:
        The assistant's reply as a plain string.

    Raises:
        RuntimeError: On API errors or unexpected response shapes.
    """
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
    }

    logger.info(f"Sending request to LLM | model={LLM_MODEL} | turns={len(messages)}")

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            # 4xx errors are client mistakes — no point retrying
            if response.status_code == 401:
                raise RuntimeError(
                    "Authentication failed. Please check your LLM_API_KEY."
                )
            if response.status_code == 429:
                raise RuntimeError(
                    "Rate limit reached. Please wait a moment and try again."
                )
            if 400 <= response.status_code < 500:
                raise RuntimeError(
                    f"Request error ({response.status_code}). Please try again."
                )

            # 5xx errors are server-side — worth retrying
            response.raise_for_status()

            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()

            if attempt > 1:
                logger.info(f"LLM responded successfully on attempt {attempt}.")
            else:
                logger.info("LLM response received successfully.")

            return reply

        except RuntimeError:
            # Our own well-formed errors — re-raise immediately, no retry
            raise

        except httpx.TimeoutException as e:
            last_error = e
            logger.warning(f"LLM request timed out (attempt {attempt}/{MAX_RETRIES}).")

        except httpx.HTTPStatusError as e:
            last_error = e
            logger.warning(
                f"LLM server error {e.response.status_code} "
                f"(attempt {attempt}/{MAX_RETRIES})."
            )

        except (KeyError, IndexError) as e:
            # Unexpected response shape — no point retrying
            logger.error(f"Unexpected LLM response shape: {e}")
            raise RuntimeError(
                "Received an unexpected response from the AI. Please try again."
            )

    # All retries exhausted
    logger.error(f"LLM request failed after {MAX_RETRIES} attempts: {last_error}")
    raise RuntimeError(
        "The AI is not responding after multiple attempts. Please try again later."
    )