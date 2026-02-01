# Zoey - AI Telegram Bot Instructions

## Project Overview
Zoey is a Telegram bot with AI-powered intent classification and reminder functionality. The bot runs in webhook mode on Fly.io and uses OpenAI for natural language understanding.

## Architecture & Message Flow

### Core Components
- **[messaging.py](messaging.py)**: Main entry point. Handles Telegram webhook server, message routing, and reminder job scheduler
- **[intents.py](intents.py)**: AI-powered intent classification and handlers. Routes messages to either reminder or chat flows
- **[reminders.py](reminders.py)**: In-memory reminder storage (list of tuples: `user_id, reminder_text, target_datetime`)

### Message Flow Pattern
1. User sends message → Telegram webhook → `handle_message()` in [messaging.py](messaging.py)
2. `determine_intent(user_message)` uses OpenAI to classify as `REMINDER` or `CHAT`
3. Route to handler:
   - **REMINDER**: `parse_reminder_details()` extracts JSON with date/time/text → `create_datetime_from_details()` → `add_reminder()` to in-memory list
   - **CHAT**: Direct OpenAI conversation with Zoey persona
4. Background job (`reminder_job`) checks every 30 seconds for due reminders

## Critical Conventions

### AI Prompt Engineering Pattern
All OpenAI calls follow a strict pattern with explicit output format instructions:
```python
# Intent classification: Single-word output only
{"role": "system", "content": "Respond with ONLY one word: 'REMINDER' or 'CHAT'"}

# Reminder parsing: Structured JSON output
{"role": "system", "content": """Extract reminder details. Respond with JSON format:
{
  "reminder_text": "...",
  "date": "YYYY-MM-DD or 'today' or 'tomorrow'",
  "time": "HH:MM (24-hour)"
}"""}
```
When adding new AI features, always specify exact output format in system prompt.

### Reminder Storage is Ephemeral
`reminders` list in [reminders.py](reminders.py) is in-memory only. No database. Reminders lost on restart. When users report missing reminders after deployment, this is expected behavior.

### Deployment Mode: Webhooks Only
Bot runs in webhook mode (`run_webhook`) for Fly.io, NOT polling mode. The webhook URL is hardcoded:
```python
webhook_url=f"https://zoey-9wkdiq.fly.dev/{token}"
```
When testing locally, must use ngrok or similar tunneling - cannot use `run_polling()` without code changes.

## Key Development Workflows

### Local Development Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Create .env with BOT_TOKEN and OPENAI_API_KEY
python messaging.py  # Requires webhook tunneling (ngrok, etc.)
```

### Testing Without Webhook (not in current code)
Current implementation requires webhook. For local testing, need to:
1. Either use ngrok tunnel: `ngrok http 8080`
2. Or modify [messaging.py](messaging.py) to use `app.run_polling()` instead

### Deployment to Fly.io
```bash
fly deploy  # Uses Dockerfile
fly secrets set BOT_TOKEN=xxx OPENAI_API_KEY=yyy
```

## Dependencies & Versions
- **python-telegram-bot==20.7**: Uses async API with `[job-queue,webhooks]` extras
- **openai==1.51.0**: Uses `AsyncOpenAI` client, NOT older sync API
- **python-dotenv==1.0.0**: Loads `.env` for local dev (Fly.io uses secrets)

## Error Handling Philosophy
Fallback to safe defaults rather than raising exceptions:
- Intent classification fails → default to `CHAT`
- Reminder parsing fails → return helpful error message string
- Date parsing fails → default to "today" or 1 hour from now
- Individual reminder send fails → log and continue to next reminder

## Integration Points

### OpenAI API Usage
- All calls use `AsyncOpenAI` with async/await
- Model: `gpt-3.5-turbo` for all intents (cost optimization)
- Max tokens: 10 for intent, 100 for reminder parsing, 100 for chat
- Always wrap in try/except with graceful fallbacks

### Telegram Bot API
- Uses context managers (`Application.builder()`)
- Job queue initialized automatically by `run_webhook()`
- Global `app` reference required for sending reminders from background job
- Message handlers use `filters.TEXT` (no commands like `/start` implemented)

## Project-Specific Gotchas

1. **Job Queue Initialization**: Job queue only exists after `run_webhook()` is called, NOT after `Application.builder().build()`

2. **DateTime Handling**: `create_datetime_from_details()` auto-advances to tomorrow if target time already passed today - prevents accidental past reminders

3. **Webhook vs URL Path**: URL path in `run_webhook()` must match the token: `url_path=token`

4. **Fly.io Port**: Hardcoded to 8080 in both [messaging.py](messaging.py) and [fly.toml](fly.toml) internal_port

5. **No Database**: When adding persistence, need to refactor [reminders.py](reminders.py) storage layer entirely
