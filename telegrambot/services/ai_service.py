"""
services/ai_service.py

Handles all communication with the AI/LLM provider.
Works with any OpenAI-compatible API (OpenRouter, OpenAI, etc.)

This is the "brain" of the bot — it takes a conversation history
and returns the AI's reply.

All settings (model, temperature, timeout, etc.) come from config.py.
If you want to change AI behaviour, edit your .env file — not this file.
"""

import logging
import httpx

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT_SECONDS,
    LLM_MAX_RETRIES,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


async def get_ai_response(messages: list[dict]) -> str:
    """
    Send a conversation history to the AI and return its reply.

    How it works:
      1. Takes the full conversation history (list of messages)
      2. Adds the system prompt at the front (AI personality/instructions)
      3. Sends everything to the LLM API
      4. Returns the AI's reply as a plain string

    Retry logic:
      - Retries up to LLM_MAX_RETRIES times on temporary errors (timeouts, 5xx)
      - Does NOT retry on permanent errors (wrong API key, bad request)

    Args:
        messages: Conversation history in the format:
                  [{"role": "user", "content": "Hello!"},
                   {"role": "assistant", "content": "Hi there!"},
                   {"role": "user", "content": "How are you?"}]

    Returns:
        The AI's reply as a plain string.

    Raises:
        RuntimeError: With a user-friendly message if something goes wrong.
    """

    # Build the request headers — this is how we authenticate with the API
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    # Build the request body — what we send to the AI
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }

    logger.info(f"Calling AI | model={LLM_MODEL} | messages in context={len(messages)}")

    # Keep track of the last error for the final error message
    last_error: Exception | None = None

    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            # Make the HTTP request to the AI API
            # We use "async with" so the connection is properly closed after
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            # --- Handle specific HTTP error codes ---
            # 401 = wrong API key — no point retrying
            if response.status_code == 401:
                raise RuntimeError(
                    "Authentication failed. Please check your LLM_API_KEY in .env"
                )

            # 429 = too many requests — tell the user to wait
            if response.status_code == 429:
                raise RuntimeError(
                    "AI rate limit reached. Please wait a moment and try again."
                )

            # Any other 4xx = something wrong with our request
            if 400 <= response.status_code < 500:
                raise RuntimeError(
                    f"Request error ({response.status_code}). Please try again."
                )

            # 5xx = server problem on the AI provider's side — worth retrying
            response.raise_for_status()

            # --- Parse the response ---
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()

            if attempt > 1:
                logger.info(f"AI responded successfully on attempt {attempt}.")
            else:
                logger.info("AI response received successfully.")

            return reply

        except RuntimeError:
            # Our own clear error messages — re-raise immediately, no retry
            raise

        except httpx.TimeoutException as e:
            # AI took too long — retry
            last_error = e
            logger.warning(f"AI request timed out (attempt {attempt}/{LLM_MAX_RETRIES}).")

        except httpx.HTTPStatusError as e:
            # Server error (5xx) — retry
            last_error = e
            logger.warning(
                f"AI server error {e.response.status_code} "
                f"(attempt {attempt}/{LLM_MAX_RETRIES})."
            )

        except (KeyError, IndexError) as e:
            # Response came back but in an unexpected format — no point retrying
            logger.error(f"Unexpected AI response format: {e}")
            raise RuntimeError(
                "Received an unexpected response from the AI. Please try again."
            )

    # If we get here, all retries failed
    logger.error(f"AI request failed after {LLM_MAX_RETRIES} attempts. Last error: {last_error}")
    raise RuntimeError(
        "The AI is not responding after multiple attempts. Please try again later."
    )
