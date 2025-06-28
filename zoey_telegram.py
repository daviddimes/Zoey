# zoey_telegram.py

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from llama_cpp import Llama
import json
import os
import string
import logging
import requests
import re
import threading
import time as time_module

# 🔑 Replace this with your actual token from BotFather
BOT_TOKEN = "7502524168:AAGqHOdpPIYQ1K9GObnK9w9o0xVka5b7Gy8"

# Load Mistral model once at startup
llm = Llama(
    model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    n_ctx=4096,
    verbose=False
)

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
    # Remove trailing punctuation and extra spaces
    cleaned_input = user_input.strip().rstrip(string.punctuation)
    lowered = cleaned_input.lower()
    # List of common question words
    question_words = (
        "what", "who", "when", "where", "why", "how", "is", "are", "do", "does", "did", "can", "could", "would", "should", "will", "am", "was", "were", "may", "might", "shall", "have", "has", "had"
    )
    # Don't save questions or commands as facts
    if cleaned_input.endswith("?") or cleaned_input.startswith("/") or lowered.startswith(question_words):
        return None
    # Pattern-based facts (still supported)
    if lowered.startswith("i am "):
        fact = cleaned_input[5:].strip()
        return f"{user_name} is {fact}"
    if lowered.startswith("i'm "):
        fact = cleaned_input[4:].strip()
        return f"{user_name} is {fact}"
    if lowered.startswith("i like "):
        fact = cleaned_input[7:].strip()
        return f"{user_name} likes {fact}"
    if lowered.startswith("my ") and " is " in lowered:
        parts = cleaned_input.split(" is ", 1)
        if len(parts) == 2:
            return f"{user_name}'s {parts[0][3:]} is {parts[1].strip()}"
    # Default: save any other statement as a fact
    return f"{user_name} said: {cleaned_input}"

# Pushover credentials (replace with your actual keys)
PUSHOVER_USER_KEY = "uzc58jcvu7hdf3r9dykjj55piobtub"
PUSHOVER_API_TOKEN = "asoyjemyxuuymxq1b3o32fehd7ez1h"

def send_pushover_reminder(message):
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": message
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        logging.error(f"Pushover error: {e}")

def parse_reminder(user_input):
    # Matches: Remind me to <task> or Remind me to <task> at <time>
    match = re.match(r"remind me to (.+?)(?: at (.+))?$", user_input, re.IGNORECASE)
    if match:
        task = match.group(1).strip(' "')
        reminder_time = match.group(2).strip(' "') if match.group(2) else None
        return task, reminder_time
    return None, None

def schedule_reminder(task, reminder_time):
    # Support 'in X minutes/hours/days/weeks/seconds' or HH:MM (24h)
    delay = None
    if reminder_time:
        m = re.match(r"in (\d+) (second|seconds|minute|minutes|hour|hours|day|days|week|weeks)", reminder_time)
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
            # Try HH:MM (24h today)
            try:
                from datetime import datetime, timedelta
                now = datetime.now()
                target = datetime.strptime(reminder_time, "%H:%M")
                target = target.replace(year=now.year, month=now.month, day=now.day)
                if target < now:
                    target += timedelta(days=1)
                delay = (target - now).total_seconds()
            except Exception:
                delay = None
    def send():
        time_module.sleep(delay or 0)
        send_pushover_reminder(f"Reminder: {task}")
    threading.Thread(target=send, daemon=True).start()

# ✅ START command — runs when you send /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Zoey is online. How can I help you, David?")

# 📥 Handles all text messages
async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_name = (update.effective_user.first_name or "User").title()
    # --- Reminder logic ---
    task, reminder_time = parse_reminder(user_input)
    if task:
        schedule_reminder(task, reminder_time)
        if reminder_time:
            await update.message.reply_text(f"Okay, I'll remind you to '{task}' at {reminder_time} via Pushover!")
        else:
            await update.message.reply_text(f"Okay, I'll remind you to '{task}' via Pushover!")
        return
    # --- Memory logic ---
    memory = load_memory()
    user_memories = memory.get(user_name, [])
    # Try to extract a fact and store it
    fact = extract_fact(user_name, user_input)
    memory_message = None
    if fact:
        fact = fact.strip()
        if fact not in [f.strip() for f in user_memories]:
            user_memories.append(fact)
            memory[user_name] = user_memories
            save_memory(memory)
            memory_message = f"(Added to memory: '{fact}')"
            logging.info(f"Added fact for {user_name}: {fact}")
        else:
            logging.info(f"Fact already in memory for {user_name}: {fact}")
    else:
        logging.info(f"No fact extracted from input: {user_input}")
    # Add user memories to prompt
    memory_section = "\n".join(f"- {m}" for m in user_memories)
    memory_prompt = f"\n{user_name}'s memory:\n{memory_section}\n" if user_memories else ""
    prompt = f"{system_message}{memory_prompt}{user_name}: {user_input}\nZoey:"
    response = llm(prompt, max_tokens=128)
    zoey_reply = response["choices"][0]["text"].strip().split("\n")[0]
    if memory_message:
        zoey_reply = f"{zoey_reply}\n{memory_message}"
    await update.message.reply_text(zoey_reply)

# 🧠 Main loop
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))

    print("Zoey Telegram Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
