# --- User tracking for broadcast ---
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(users), f, indent=2)

def add_user(chat_id):
    users = load_users()
    users.add(chat_id)
    save_users(users)

# zoey_telegram.py

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json
import os
import string
import logging
import requests
import re
import threading
import time as time_module
import dateutil.parser

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # If python-dotenv is not installed, skip loading .env

# 🔑 Replace this with your actual token from BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# 🧠 Groq API Setup
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def call_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.1-8b-instant",  # updated to your chosen model
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    res = requests.post(url, headers=headers, json=data)
    try:
        response_json = res.json()
        if "choices" in response_json:
            return response_json["choices"][0]["message"]["content"]
        else:
            print("Groq API error:", response_json)
            return "Sorry, there was a problem with the Groq API: " + str(response_json)
    except Exception as e:
        print("Groq error response:", res.status_code, res.text)
        raise


# System prompt for Zoey
system_message = (
    "You are Zoey. You are a friendly, casual, and helpful assistant. You always let the user lead the conversation. "
    "You do not ask questions unless directly asked. You do not offer your opinions unless they are specifically requested "
    "or directly relevant to the current topic. You never go off topic. You do not mention being an AI. "
    "You respond clearly and efficiently. You avoid rambling, repetition, or adding fluff. "
    "You only act when spoken to, and you only talk about what the user is talking about. "
    "Before answering, you silently think through your response, then reply clearly and intelligently. "
    "Only mention facts from your memory if they are directly relevant to the user's current message or question. "
    "Do not bring up unrelated memories."
)

MEMORY_FILE = "memory/memory.json"

def ensure_memory_dir():
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)

def load_memory():
    ensure_memory_dir()
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    ensure_memory_dir()
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def extract_fact(user_name, user_input):
    cleaned_input = user_input.strip().rstrip(string.punctuation)
    lowered = cleaned_input.lower()
    question_words = (
        "what", "who", "when", "where", "why", "how", "is", "are", "do", "does", "did", "can", "could", "would", "should", "will", "am", "was", "were", "may", "might", "shall", "have", "has", "had"
    )
    if cleaned_input.endswith("?") or cleaned_input.startswith("/") or lowered.startswith(question_words):
        return None
    if lowered.startswith("i am "):
        return f"{user_name} is {cleaned_input[5:].strip()}"
    if lowered.startswith("i'm "):
        return f"{user_name} is {cleaned_input[4:].strip()}"
    if lowered.startswith("i like "):
        return f"{user_name} likes {cleaned_input[7:].strip()}"
    if lowered.startswith("my ") and " is " in lowered:
        parts = cleaned_input.split(" is ", 1)
        if len(parts) == 2:
            return f"{user_name}'s {parts[0][3:]} is {parts[1].strip()}"
    return f"{user_name} said: {cleaned_input}"



def parse_reminder(user_input):
    # Support both 'remind me to [task] at [time]' and 'remind me to [task] in [duration]'
    match = re.match(r"remind me to (.+?)(?: (?:at|in) (.+))?$", user_input, re.IGNORECASE)
    if match:
        task = match.group(1).strip(' "')
        reminder_time = match.group(2).strip(' "') if match.group(2) else None
        return task, reminder_time
    return None, None

def schedule_reminder(task, reminder_time):
    delay = None
    if reminder_time:
        # Match both 'in 1 minute' and '1 minute', '5 hours', etc.
        m = re.match(r"(?:in )?(\d+) (second|seconds|minute|minutes|hour|hours|day|days|week|weeks)", reminder_time)
        if m:
            num = int(m.group(1))
            unit = m.group(2)
            if 'second' in unit:
                delay = num
            elif 'minute' in unit:
                delay = num * 60
            elif 'hour' in unit:
                delay = num * 60 * 60
            elif 'day' in unit:
                delay = num * 60 * 60 * 24
            elif 'week' in unit:
                delay = num * 60 * 60 * 24 * 7
        else:
            try:
                from datetime import datetime, timedelta
                now = datetime.now()
                # Try parsing with dateutil for flexible time input (e.g., '10:30pm', '7:15 AM')
                target = dateutil.parser.parse(reminder_time, default=now)
                # If the parsed time is in the past, schedule for next day
                if target < now:
                    target = target + timedelta(days=1)
                delay = (target - now).total_seconds()
                if delay <= 0:
                    logging.error(f"Parsed reminder time is not in the future: {reminder_time} (delay={delay})")
                    delay = None
            except Exception as e:
                logging.error(f"Could not parse reminder time: {reminder_time} ({e})")
                delay = None
    # Use JobQueue for reminders
    def schedule_with_jobqueue(context, chat_id):
        context.application.job_queue.run_once(
            lambda ctx: ctx.bot.send_message(chat_id=chat_id, text=f"⏰ Reminder: {task}"),
            delay if delay is not None and delay > 0 else 0
        )
    return schedule_with_jobqueue

# ✅ START command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Track user on /start
    add_user(update.effective_chat.id)
    await update.message.reply_text("Hello! How can I help?")

# 📥 Message handler
async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Track user on any message
    add_user(update.effective_chat.id)
    user_input = update.message.text
    user_name = (update.effective_user.first_name or "User").title()

    task, reminder_time = parse_reminder(user_input)
    if task:
        schedule_with_jobqueue = schedule_reminder(task, reminder_time)
        chat_id = update.effective_chat.id
        schedule_with_jobqueue(context, chat_id)
        if reminder_time:
            await update.message.reply_text(f"Okay, I'll remind you to '{task}' at {reminder_time} here on Telegram!")
        else:
            await update.message.reply_text(f"Okay, I'll remind you to '{task}' here on Telegram!")
        return

    memory = load_memory()
    user_memories = memory.get(user_name, [])

    fact = extract_fact(user_name, user_input)
    # Remove memory_message and do not append it to the reply
    if fact:
        fact = fact.strip()
        if fact not in [f.strip() for f in user_memories]:
            user_memories.append(fact)
            memory[user_name] = user_memories
            save_memory(memory)
            logging.info(f"Added fact for {user_name}: {fact}")
        else:
            logging.info(f"Fact already in memory for {user_name}: {fact}")
    else:
        logging.info(f"No fact extracted from input: {user_input}")

    memory_section = "\n".join(f"- {m}" for m in user_memories)
    memory_prompt = f"\n{user_name}'s memory:\n{memory_section}\n" if user_memories else ""
    prompt = f"{system_message}{memory_prompt}{user_name}: {user_input}\nZoey:"
    zoey_reply = call_groq(prompt).strip().split("\n")[0]
    await update.message.reply_text(zoey_reply)

# --- Broadcast command (admin only) ---
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))  # Set your Telegram user ID in .env

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Always log the admin user ID and the sender's user ID for debugging
    logging.info(f"ADMIN_USER_ID: {ADMIN_USER_ID}, Sender: {update.effective_user.id}")
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = " ".join(context.args)
    users = load_users()
    count = 0
    for chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            count += 1
        except Exception as e:
            logging.error(f"Failed to send to {chat_id}: {e}")
    await update.message.reply_text(f"Broadcast sent to {count} users.")

# 🧠 Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))
    print("Zoey Telegram Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
