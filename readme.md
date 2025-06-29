# Zoey AI Telegram Bot

A Telegram chatbot powered by the Groq API (llama-3.1-8b-instant) and deployed for 24/7 operation on cloud platforms.

## Features
- Uses [Groq API](https://console.groq.com/docs) (llama-3.1-8b-instant) for all LLM responses
- Telegram bot built with [python-telegram-bot](https://docs.python-telegram-bot.org/en/v20.7/)
- Async API for fast, scalable messaging
- Memory system for chat context
- Deployable to [Render](https://render.com/), [Railway](https://railway.app/), [Fly.io](https://fly.io/), or [Replit](https://replit.com/)
- Docker support for local/cloud deployment

## Environment Variables
- `BOT_TOKEN` — Telegram bot token ([Telegram BotFather](https://core.telegram.org/bots#botfather))
- `GROQ_API_KEY` — Groq API key ([Groq Console](https://console.groq.com/))
- (Optional) `PUSHOVER_USER_KEY` and `PUSHOVER_API_TOKEN` for [Pushover](https://pushover.net/) notifications

## Deployment
- [Fly.io Python Deploy Docs](https://fly.io/docs/languages-and-frameworks/python/)

## Requirements
- Python 3.10.13 (see `runtime.txt`)
- [python-telegram-bot==20.7](https://pypi.org/project/python-telegram-bot/20.7/)
- [requests](https://pypi.org/project/requests/)

## Quick Start
1. Clone this repo and install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Set environment variables for your secrets (see above).
3. Run the bot:
   ```sh
   python main.py
   ```

## License
MIT