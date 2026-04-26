"""
api.py

A simple FastAPI web API that exposes the bot's AI functionality over HTTP.
Runs alongside the Telegram bot — both share the same database and AI service.

Endpoints:
    GET  /health              — check if the API is running
    POST /chat                — send a message and get an AI reply
    GET  /history/{user_id}   — retrieve a user's conversation history
    DELETE /history/{user_id} — clear a user's conversation history

How to run (separately from the bot):
    uvicorn api:app --reload --port 8000

Then test it at:
    http://localhost:8000/docs   ← interactive API docs (built into FastAPI)
"""

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import validate_config
from database.db import (
    init_db,
    save_user,
    save_message,
    get_history,
    delete_last_message,
    reset_history,
    get_history_length,
)
from services.ai_service import get_ai_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

# Validate config and initialise DB when the API starts
validate_config()
init_db()

app = FastAPI(
    title="Telegram AI Bot API",
    description=(
        "REST API for the Telegram AI chatbot. "
        "Shares the same database and AI service as the Telegram bot."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
# Pydantic models define the shape of data coming in and going out.
# FastAPI uses these for automatic validation and documentation.

class ChatRequest(BaseModel):
    """What the client sends to /chat."""
    user_id: int          # a numeric ID to track conversation history
    message: str          # the user's message text

    class Config:
        # Example shown in the interactive docs at /docs
        json_schema_extra = {
            "example": {
                "user_id": 123456,
                "message": "What is the capital of France?"
            }
        }


class ChatResponse(BaseModel):
    """What /chat sends back."""
    user_id: int
    message: str          # the original message
    reply: str            # the AI's response
    history_length: int   # how many messages are now stored for this user


class HistoryMessage(BaseModel):
    """A single message in a conversation."""
    role: str             # "user" or "assistant"
    content: str          # the message text


class HistoryResponse(BaseModel):
    """What /history/{user_id} sends back."""
    user_id: int
    messages: list[HistoryMessage]
    total: int            # total number of messages


class StatusResponse(BaseModel):
    """What /health sends back."""
    status: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=StatusResponse,
    summary="Health check",
    description="Returns OK if the API is running.",
)
async def health_check():
    """Simple health check — useful for uptime monitoring and deployment checks."""
    return StatusResponse(status="ok", message="API is running.")


@app.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message and get an AI reply",
    description=(
        "Send a message for a given user_id. "
        "The API remembers conversation history per user_id, "
        "just like the Telegram bot does."
    ),
)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.

    Flow:
        1. Validate the message isn't empty
        2. Save the user to the database
        3. Save the user's message
        4. Load full conversation history
        5. Call the AI
        6. On failure — roll back the saved message
        7. Save the AI reply
        8. Return the reply
    """

    # Step 1: Validate input
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    logger.info(f"API /chat — user_id={request.user_id} | message={message[:80]!r}")

    # Step 2: Save user (using user_id as both id and display name for API users)
    save_user(
        user_id=request.user_id,
        username=f"api_user_{request.user_id}",
        first_name="API User",
    )

    # Step 3: Save the user's message
    save_message(user_id=request.user_id, role="user", content=message)

    # Step 4: Load conversation history
    history = get_history(user_id=request.user_id)

    # Step 5: Call the AI
    try:
        reply = await get_ai_response(history)
    except RuntimeError as e:
        # Step 6: Roll back on failure
        delete_last_message(request.user_id)
        logger.warning(f"AI error for API user {request.user_id}: {e}")
        raise HTTPException(status_code=502, detail=str(e))

    # Step 7: Save the AI's reply
    save_message(user_id=request.user_id, role="assistant", content=reply)

    # Step 8: Return the response
    return ChatResponse(
        user_id=request.user_id,
        message=message,
        reply=reply,
        history_length=get_history_length(request.user_id),
    )


@app.get(
    "/history/{user_id}",
    response_model=HistoryResponse,
    summary="Get conversation history",
    description="Returns the stored conversation history for a given user_id.",
)
async def get_conversation_history(user_id: int):
    """
    Retrieve the conversation history for a user.
    Returns an empty list if the user has no history.
    """
    logger.info(f"API /history — user_id={user_id}")

    messages = get_history(user_id=user_id)

    return HistoryResponse(
        user_id=user_id,
        messages=[HistoryMessage(role=m["role"], content=m["content"]) for m in messages],
        total=len(messages),
    )


@app.delete(
    "/history/{user_id}",
    response_model=StatusResponse,
    summary="Clear conversation history",
    description="Deletes all stored messages for a given user_id.",
)
async def clear_conversation_history(user_id: int):
    """
    Clear the conversation history for a user.
    Equivalent to the /reset command in the Telegram bot.
    """
    logger.info(f"API DELETE /history — user_id={user_id}")

    count = reset_history(user_id=user_id)

    return StatusResponse(
        status="ok",
        message=f"Cleared {count} message(s) for user {user_id}.",
    )
