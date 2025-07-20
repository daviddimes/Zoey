# Zoey AI Telegram Bot

A Telegram chatbot powered by the Open AI (GPT 4.1) and deployed for 24/7 operation on cloud platforms.

## Features
- Uses OpenAi GPT 4.1 for all LLM responses
- Telegram bot built with [python-telegram-bot](https://docs.python-telegram-bot.org/en/v20.7/)
- Async API for fast, scalable messaging
- Memory system for chat context
- Deployable to [Fly.io](https://fly.io/)
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
