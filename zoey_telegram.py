# Utility: Clean old string-based memory entries from memory.json
def clean_old_memory():
    memory = load_memory()
    cleaned = {}
    changed = False
    for user, entries in memory.items():
        if isinstance(entries, list):
            new_entries = [e for e in entries if isinstance(e, dict)]
            if len(new_entries) != len(entries):
                changed = True
            cleaned[user] = new_entries
        else:
            cleaned[user] = entries
    if changed:
        save_memory(cleaned)
        print("Old string-based memory entries removed from memory.json.")
    else:
        print("No old memory entries found to clean.")

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
from openai import OpenAI
import re
import threading
import time as time_module
import datetime
import dateutil.parser

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # If python-dotenv is not installed, skip loading .env

# 🔑 Replace this with your actual token from BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN")




# OpenAI API Setup
OPENAI_API_KEY = os.environ.get("OpenAi")
PROMPT_ID = "pmpt_687c5b2bf4288190937b95f0b281662605eca0f1bc4ae3cd"

client = OpenAI(api_key=OPENAI_API_KEY)

def call_openai(prompt):
    try:
        print("[OpenAI Request] Prompt sent:")
        print(prompt)
        response = client.responses.create(
            prompt={
                "id": PROMPT_ID,
                "version": "3"
            },
            input=prompt
        )
        # Try to extract the actual text from response.output[0].content[0].text
        if hasattr(response, "output") and response.output:
            first_output = response.output[0]
            if hasattr(first_output, "content") and first_output.content:
                first_content = first_output.content[0]
                if hasattr(first_content, "text"):
                    reply = first_content.text.strip()
                    # Hard limit: cut reply at 100 tokens, even if mid-word
                    token_count = 0
                    result = []
                    for word in re.finditer(r'\S+', reply):
                        token_count += 1
                        if token_count > 100:
                            break
                        result.append(word.group())
                    return ' '.join(result)
        return str(response)
    except Exception as e:
        print("OpenAI error response:", str(e))



# --- Hybrid Behavioral Memory ---
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

# Memory schema: { "tag": ..., "condition": ..., "value": ... }
def get_user_memory(user_name):
    memory = load_memory()
    return memory.get(user_name, [])

def add_user_memory(user_name, tag, condition, value):
    memory = load_memory()
    user_memories = memory.get(user_name, [])
    entry = {"tag": tag, "condition": condition, "value": value}
    if entry not in user_memories:
        user_memories.append(entry)
        memory[user_name] = user_memories
        save_memory(memory)
        logging.info(f"Added behavioral memory for {user_name}: {entry}")
    else:
        logging.info(f"Behavioral memory already exists for {user_name}: {entry}")

def apply_behavioral_memory(user_name, user_input):
    """
    Returns a dict of behavioral flags based on user's memory and input.
    Only applies memory if condition matches user_input.
    Example output: {"concise": True, "prefer_texting": True}
    """
    flags = {}
    user_memories = get_user_memory(user_name)
    for entry in user_memories:
        if not isinstance(entry, dict):
            continue  # Ignore old string-based memory entries
        tag = entry.get("tag", "")
        condition = entry.get("condition", "")
        value = entry.get("value", "")
        # Example: if condition is "reply_length" and value is "short"
        if condition == "reply_length" and value == "short":
            flags["concise"] = True
        if condition == "communication" and value == "texting":
            flags["prefer_texting"] = True
        if condition == "location":
            flags["location"] = value
        # Add more behaviors as needed, only if memory matches
    return flags


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


# --- Persistent Reminders ---
REMINDERS_FILE = "reminders.json"

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_reminders(reminders):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, indent=2)

def add_reminder(chat_id, task, due_time):
    reminders = load_reminders()
    logging.info(f"Adding reminder: chat_id={chat_id}, task='{task}', due_time={due_time.isoformat()}")
    reminders.append({
        "chat_id": chat_id,
        "task": task,
        "due_time": due_time.isoformat()
    })
    save_reminders(reminders)

def parse_due_time(reminder_time):
    if not reminder_time:
        logging.info("No reminder_time provided, returning None.")
        return None
    m = re.match(r"(?:in )?(\d+) (second|seconds|minute|minutes|hour|hours|day|days|week|weeks)", reminder_time)
    now = datetime.datetime.now()
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        due = None
        if 'second' in unit:
            due = now + datetime.timedelta(seconds=num)
        elif 'minute' in unit:
            due = now + datetime.timedelta(minutes=num)
        elif 'hour' in unit:
            due = now + datetime.timedelta(hours=num)
        elif 'day' in unit:
            due = now + datetime.timedelta(days=num)
        elif 'week' in unit:
            due = now + datetime.timedelta(weeks=num)
        logging.info(f"Parsed relative reminder time '{reminder_time}' as {due.isoformat()}.")
        return due
    else:
        try:
            # If reminder_time matches a time-only string (like '9pm'), parse just the hour/minute
            time_match = re.match(r"^(\d{1,2})(:(\d{2}))? ?([ap]m)?$", reminder_time.strip(), re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(3)) if time_match.group(3) else 0
                ampm = time_match.group(4)
                if ampm:
                    if ampm.lower() == 'pm' and hour < 12:
                        hour += 12
                    if ampm.lower() == 'am' and hour == 12:
                        hour = 0
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target < now:
                    target = target + datetime.timedelta(days=1)
                logging.info(f"Parsed time-only reminder '{reminder_time}' as {target.isoformat()}.")
                return target
            # Otherwise, fallback to full parse
            target = dateutil.parser.parse(reminder_time, default=now)
            if target < now:
                target = target + datetime.timedelta(days=1)
            logging.info(f"Parsed absolute reminder time '{reminder_time}' as {target.isoformat()}.")
            return target
        except Exception as e:
            logging.error(f"Could not parse reminder time: {reminder_time} ({e})")
            return None

def start_reminder_polling(application):
    async def poll_reminders():
        while True:
            reminders = load_reminders()
            now = datetime.datetime.now()
            logging.info(f"Polling reminders at {now.isoformat()}. Reminders loaded: {len(reminders)}")
            to_send = [r for r in reminders if datetime.datetime.fromisoformat(r["due_time"]) <= now]
            if to_send:
                logging.info(f"Reminders to send: {len(to_send)}")
                for r in to_send:
                    try:
                        logging.info(f"Sending reminder to chat_id={r['chat_id']}: {r['task']}")
                        await application.bot.send_message(chat_id=r["chat_id"], text=f"⏰ Reminder: {r['task']}")
                    except Exception as e:
                        logging.error(f"Failed to send reminder to {r['chat_id']}: {e}")
                reminders = [r for r in reminders if datetime.datetime.fromisoformat(r["due_time"]) > now]
                save_reminders(reminders)
            await asyncio.sleep(10)
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(poll_reminders())

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
        due_time = parse_due_time(reminder_time) if reminder_time else None
        if due_time:
            add_reminder(update.effective_chat.id, task, due_time)
            await update.message.reply_text(f"Okay, I'll remind you to '{task}' at {reminder_time} here on Telegram!")
        else:
            add_reminder(update.effective_chat.id, task, datetime.datetime.now())
            await update.message.reply_text(f"Okay, I'll remind you to '{task}' here on Telegram!")
        return

    # --- Behavioral memory ---
    behavioral_flags = apply_behavioral_memory(user_name, user_input)

    # Check for direct time-related questions and answer directly
    time_patterns = [
        r"^what(?:'s| is) the time[\?\.! ]*$",
        r"^current time[\?\.! ]*$",
        r"^time now[\?\.! ]*$",
        r"^what time is it[\?\.! ]*$",
        r"^tell me the time[\?\.! ]*$"
    ]
    if any(re.match(p, user_input.strip(), re.IGNORECASE) for p in time_patterns):
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p on %A, %B %d, %Y")
        await update.message.reply_text(f"It's {time_str}.")
        return

    # Example: if user prefers concise replies, adjust prompt
    prompt_instruction = ""
    if behavioral_flags.get("concise"):
        prompt_instruction = " (reply concisely)"
    # Example: if user prefers texting, add a hint (not injected unless relevant)
    # Example: if location is set, could filter info (not implemented unless memory exists)

    # Build prompt WITHOUT injecting memory
    prompt = f"{user_name}: {user_input}\nZoey{prompt_instruction}:"
    zoey_reply = call_openai(prompt).strip()
    # --- Link formatting ---
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    links = link_pattern.findall(zoey_reply)
    heading_pos = zoey_reply.find('\n##') if '\n##' in zoey_reply else len(zoey_reply)
    main_text = zoey_reply[:heading_pos].strip()
    max_length = 4096
    if main_text:
        for i in range(0, len(main_text), max_length):
            await update.message.reply_text(main_text[i:i+max_length])
    if links:
        sent_urls = set()
        for text, url in links:
            if url not in sent_urls:
                await update.message.reply_text(url)
                sent_urls.add(url)

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

# --- Reminders command
async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reminders = load_reminders()
    user_reminders = [r for r in reminders if r["chat_id"] == chat_id]
    if not user_reminders:
        await update.message.reply_text("You have no scheduled reminders.")
        return
    lines = []
    for r in user_reminders:
        try:
            due = datetime.datetime.fromisoformat(r["due_time"])
            due_str = due.strftime("%I:%M %p on %A, %B %d, %Y")
        except Exception:
            due_str = r["due_time"]
        lines.append(f"- {r['task']} at {due_str}")
    reply = "Your scheduled reminders:\n" + "\n".join(lines)
    await update.message.reply_text(reply)

# 🧠 Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("reminders", reminders_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))
    start_reminder_polling(app)
    print("Zoey Telegram Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
