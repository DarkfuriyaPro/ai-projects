# Telegram AI Chatbot

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21.6-blue?style=flat)
![OpenRouter](https://img.shields.io/badge/OpenRouter-API-6B4FBB?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

A production-ready AI chatbot for Telegram, built with Python. Integrates with any OpenAI-compatible LLM provider (OpenRouter, OpenAI, etc.) and maintains per-user conversation memory across the entire session.

---

## Features

- **Conversation memory** — each user gets their own isolated chat history, enabling natural multi-turn conversations
- **Retry logic** — automatic retries on transient network or server errors
- **Async architecture** — fully async via `httpx` and `python-telegram-bot` v21
- **Robust error handling** — granular error messages for timeouts, rate limits, and auth failures
- **Clean modular structure** — separated concerns across `bot`, `config`, `memory`, and `llm_client`
- **User commands** — `/start`, `/help`, `/reset` with smart responses
- **Secret-safe logging** — API keys are masked in all log output

---

## Project Structure

```
telegram-ai-bot/
├── bot.py            # Entry point — handlers, routing, error handler
├── config.py         # Environment variables & validation
├── memory.py         # Per-user conversation history manager
├── llm_client.py     # Async LLM API wrapper (OpenAI-compatible)
├── requirements.txt  # Pinned dependencies
├── .env.example      # Environment variable template
└── README.md         # This file
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Telegram framework | python-telegram-bot 21.6 |
| HTTP client | httpx (async) |
| LLM provider | OpenRouter (OpenAI-compatible) |
| Config management | python-dotenv |

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/telegram-ai-bot.git
cd telegram-ai-bot
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
LLM_API_KEY=your-openrouter-api-key-here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-3.5-turbo
```

> **Get your Telegram bot token** — open [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, and follow the steps.
>
> **Get your OpenRouter API key** — sign up at [openrouter.ai](https://openrouter.ai) and generate a key from the dashboard. Many models have a free tier.

### 5. Run the bot

```bash
python bot.py
```

You should see:
```
2024-01-01 12:00:00 | INFO | __main__ | Config loaded — ...
2024-01-01 12:00:00 | INFO | __main__ | Starting Telegram AI Bot...
2024-01-01 12:00:00 | INFO | __main__ | Bot is running. Press Ctrl+C to stop.
```

Open Telegram, find your bot, and start chatting!

---

## Usage

### Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and command overview |
| `/help` | Detailed usage guide and example prompts |
| `/reset` | Clear your conversation history and start fresh |

### Example conversation

```
You:  My name is Alex and I'm learning Python.
Bot:  Nice to meet you, Alex! Python is a great choice...

You:  What's a good first project for me?
Bot:  Given that you're just starting out, Alex, I'd suggest...

You:  /reset
Bot:  🗑 Conversation reset. Cleared 4 messages from our history.
```

> The bot remembers context across the full session (up to 20 messages).
> Use `/reset` any time to start a fresh conversation.

---

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Token from [@BotFather](https://t.me/BotFather) |
| `LLM_API_KEY` | Yes | — | API key for your LLM provider |
| `LLM_BASE_URL` | No | `https://openrouter.ai/api/v1` | Base URL for the LLM API |
| `LLM_MODEL` | No | `openai/gpt-3.5-turbo` | Model identifier |

### Switching LLM providers

**OpenAI directly:**
```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

**Other OpenRouter models:**
```env
LLM_MODEL=anthropic/claude-3-haiku
LLM_MODEL=meta-llama/llama-3-8b-instruct
LLM_MODEL=google/gemma-2-9b-it:free
```

---

## Module Overview

### `bot.py`
Main entry point. Registers all command and message handlers, configures logging, and starts the polling loop. Contains a global error handler that catches unexpected exceptions across all handlers.

### `config.py`
Loads environment variables via `python-dotenv`. Provides `validate_config()` which raises a clear error on startup if required variables are missing, and `debug_summary()` which logs config state without exposing secrets.

### `memory.py`
In-memory conversation store using a `defaultdict`. Each user gets an isolated list of role/content message dicts. Automatically trims history to `MAX_HISTORY_LENGTH = 20` messages. Provides `pop_last_message()` for safe rollback on LLM failure.

### `llm_client.py`
Async wrapper around any OpenAI-compatible `/chat/completions` endpoint. Injects a system prompt, handles retries (up to 2 attempts) on transient errors, and raises descriptive `RuntimeError` exceptions for clean error propagation to the user.

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

---

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

---

## Author

Built by **[Kira Telegina]** · [GitHub](https://github.com/DarkfuriyaPro/ai-projects.git)
