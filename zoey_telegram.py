# zoey_telegram.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import json
import os
import string
import logging
import requests
from openai import OpenAI
import base64
import re
import threading
import time as time_module
import datetime
import dateutil.parser
# --- Commands list ---
async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Commands", callback_data="cmd_showcommands")]
    ])
    commands = [
        "/start - Start Zoey and track you as a user",
        "/reminders - List your scheduled reminders",
        "/broadcast <message> - Send a message to all users (admin only)",
        "/commands - Show this list of commands",
        "remind me to [task] at [time] - Schedule a reminder",
        "remind me to [task] in [duration] - Schedule a reminder",
        "play [song/artist/playlist/podcast] - Get a Spotify link for music or podcast",
        "play artist [name] - Get a Spotify link for an artist",
        "play playlist [name] - Get a Spotify link for a playlist",
        "play podcast [name] - Get a Spotify link for a podcast",
        "Ask any question or chat with Zoey"
    ]
    reply = "Available commands and features:\n\n" + "\n".join(commands)
    await update.message.reply_text(reply, reply_markup=inline_keyboard)

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
ASSISTANT_ID = "asst_SJYzPpk8umNdaG3QiUI3IIp4"

# Spotify API Setup
SPOTIFY_KEY = os.environ.get("SpotifyKey")
SPOTIFY_CLIENT_ID = None
SPOTIFY_CLIENT_SECRET = None
if SPOTIFY_KEY and ':' in SPOTIFY_KEY:
    SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET = SPOTIFY_KEY.split(':', 1)


# --- OpenAI Assistants API integration ---
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

def call_openai(prompt):
    try:
        print("[OpenAI Assistant Request] Prompt sent:")
        print(prompt)
        # Create a new thread for each user message
        thread = client.beta.threads.create()
        # Add the user message to the thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        # Wait for the run to complete
        import time
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            elif run_status.status in ("failed", "cancelled", "expired"):
                return "[Zoey Assistant Error: Run failed or cancelled]"
            time.sleep(1)
        # Get the latest assistant message
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                return msg.content[0].text.value.strip()
        return "[Zoey Assistant Error: No response]"
    except Exception as e:
        print("OpenAI Assistant error response:", str(e))
        return f"[Zoey Assistant Error: {str(e)}]"



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
                # Only set for tomorrow if the time has already passed
                if target > now:
                    logging.info(f"Parsed time-only reminder '{reminder_time}' as {target.isoformat()} (today).")
                    return target
                else:
                    target = target + datetime.timedelta(days=1)
                    logging.info(f"Parsed time-only reminder '{reminder_time}' as {target.isoformat()} (tomorrow).")
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
    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Commands", callback_data="cmd_showcommands")]
    ])
    await update.message.reply_text(
        "Hello! How can I help? Tap 'Commands' below to see available commands.",
        reply_markup=inline_keyboard
    )
# --- Inline command handler ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "cmd_showcommands":
        commands_buttons = [
            [InlineKeyboardButton("Set Reminder", callback_data="cmd_setreminder")],
            [InlineKeyboardButton("View Reminders", callback_data="cmd_viewreminders")],
            [InlineKeyboardButton("Broadcast", callback_data="cmd_broadcast")],
            [InlineKeyboardButton("Add Contact", callback_data="cmd_addcontact")],
            [InlineKeyboardButton("View Contacts", callback_data="cmd_viewcontacts")],
            [InlineKeyboardButton("Delete Contact", callback_data="cmd_deletecontact")],
            [InlineKeyboardButton("Play Music", callback_data="cmd_playmusic")],
        ]
        keyboard = InlineKeyboardMarkup(commands_buttons)
        await query.edit_message_text(
            "Available commands:", reply_markup=keyboard
        )
    elif data == "cmd_setreminder":
        user_id = str(query.from_user.id)
        pending_reminder[user_id] = {"step": 1}
        await query.edit_message_text("What is the reminder?")
    elif data == "cmd_viewreminders":
        await reminders_command(update, context)
    elif data == "cmd_broadcast":
        await query.edit_message_text("To broadcast, type /broadcast <message> (admin only).")
    elif data == "cmd_addcontact":
        user_id = str(query.from_user.id)
        pending_contact[user_id] = {"step": 1}
        await addcontact_command(update, context)
    elif data == "cmd_viewcontacts":
        await viewcontacts_command(update, context)
    elif data == "cmd_deletecontact":
        await deletecontact_command(update, context)
    elif data == "cmd_playmusic":
        await query.edit_message_text("To play music, type: play [song/artist/playlist/podcast]")
    elif data.startswith("reminder_"):
        user_id = str(query.from_user.id)
        # Only route time/date quick-pick buttons to reminder flow
        if user_id in pending_reminder and data in [
            "reminder_time_15min", "reminder_time_1hr", "reminder_time_manual",
            "reminder_date_today", "reminder_date_tomorrow", "reminder_date_manual"
        ]:
            class DummyUser:
                def __init__(self, id):
                    self.id = id
            class DummyChat:
                def __init__(self, id):
                    self.id = id
            class DummyUpdate:
                def __init__(self, callback_query, user_id):
                    self.callback_query = callback_query
                    self.effective_user = DummyUser(user_id)
                    self.effective_chat = DummyChat(user_id)
            dummy_update = DummyUpdate(query, query.from_user.id)
            await handle_set_reminder_flow(dummy_update, context)
        else:
            await reminder_callback_handler(update, context)
    elif data.startswith("delete_contact_"):
        await handle_delete_contact_button(update, context)
    else:
        await query.edit_message_text("Unknown command.")

# 📥 Message handler
async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Track user on any message
    add_user(update.effective_chat.id)
    user_input = update.message.text
    user_name = (update.effective_user.first_name or "User").title()

    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Commands", callback_data="cmd_showcommands")]
    ])

    # --- Contact flow ---
    user_id = str(update.effective_user.id)
    if user_id in pending_contact:
        if await handle_add_contact_flow(update, context):
            return
    # --- Reminder flow ---
    user_id = str(update.effective_user.id)
    if user_id in pending_reminder:
        if await handle_set_reminder_flow(update, context):
            return

    # --- Relay message to contact if pattern matches ---
    if await try_relay_message(update, context, user_input):
        return

    # Spotify play command
    play_match = re.match(r"play (.+)", user_input.strip(), re.IGNORECASE)
    if play_match:
        play_query = play_match.group(1).strip()
        # Try to guess type: playlist, artist, podcast, or track
        type_ = "track"
        if "playlist" in play_query.lower():
            type_ = "playlist"
            play_query = play_query.replace("playlist", "", 1).strip()
        elif "artist" in play_query.lower():
            type_ = "artist"
            play_query = play_query.replace("artist", "", 1).strip()
        elif "podcast" in play_query.lower():
            type_ = "show"
            play_query = play_query.replace("podcast", "", 1).strip()
        result = spotify_search_play(play_query, type_)
        await update.message.reply_text(result, reply_markup=inline_keyboard)
        return

    task, reminder_time = parse_reminder(user_input)
    if task:
        due_time = parse_due_time(reminder_time) if reminder_time else None
        if due_time:
            add_reminder(update.effective_chat.id, task, due_time)
            await update.message.reply_text(f"Okay, I'll remind you to '{task}' at {reminder_time} here on Telegram!", reply_markup=inline_keyboard)
        else:
            add_reminder(update.effective_chat.id, task, datetime.datetime.now())
            await update.message.reply_text(f"Okay, I'll remind you to '{task}' here on Telegram!", reply_markup=inline_keyboard)
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
        await update.message.reply_text(f"It's {time_str}.", reply_markup=inline_keyboard)
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
            await update.message.reply_text(main_text[i:i+max_length], reply_markup=inline_keyboard)
    if links:
        sent_urls = set()
        for text, url in links:
            if url not in sent_urls:
                await update.message.reply_text(url, reply_markup=inline_keyboard)
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

# --- Spotify API functions ---
def get_spotify_token():
    if not SPOTIFY_KEY:
        return "ERROR: SpotifyKey environment variable is missing."
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return "ERROR: SpotifyKey is not in the format 'client_id:client_secret'."
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    resp = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return f"ERROR: Spotify authentication failed (status {resp.status_code}). Check your client ID and secret."

def spotify_search_play(query, type_):
    token = get_spotify_token()
    if isinstance(token, str) and token.startswith("ERROR:"):
        return token
    if not token:
        return "Spotify API authentication failed."
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": query, "type": type_, "limit": 1}
    resp = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)
    if resp.status_code == 200:
        result = resp.json()
        if type_ == "track" and result.get("tracks", {}).get("items"):
            track = result["tracks"]["items"][0]
            name = track["name"]
            artist = track["artists"][0]["name"]
            url = track["external_urls"]["spotify"]
            return f"Play '{name}' by {artist}: {url}"
        elif type_ == "artist" and result.get("artists", {}).get("items"):
            artist = result["artists"]["items"][0]
            name = artist["name"]
            url = artist["external_urls"]["spotify"]
            return f"Play artist '{name}': {url}"
        elif type_ == "playlist" and result.get("playlists", {}).get("items"):
            playlist = result["playlists"]["items"][0]
            name = playlist["name"]
            url = playlist["external_urls"]["spotify"]
            return f"Play playlist '{name}': {url}"
        elif type_ == "show" and result.get("shows", {}).get("items"):
            show = result["shows"]["items"][0]
            name = show["name"]
            url = show["external_urls"]["spotify"]
            return f"Play podcast '{name}': {url}"
        else:
            return f"No {type_} found for '{query}'."
    return f"Spotify search failed (status {resp.status_code})."

# --- Reminders command
def get_user_reminders(user_id):
    import json
    try:
        with open("reminders.json", "r") as f:
            reminders = json.load(f)
    except Exception:
        reminders = []
    # Use chat_id for matching
    return [r for r in reminders if str(r.get("chat_id")) == str(user_id)]

async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)
    reminders = get_user_reminders(user_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Commands", callback_data="cmd_showcommands")]
    ])
    if not reminders:
        text = "You have no reminders set."
    else:
        text = "Your reminders:\n"
        for r in reminders:
            dt = r.get("due_time")
            try:
                import datetime
                dt_obj = datetime.datetime.fromisoformat(dt)
                dt_str = dt_obj.strftime("%I:%M %p on %B %d, %Y")
            except Exception:
                dt_str = dt
            text += f"- {r.get('task')} at {dt_str}\n"
    await update.effective_message.reply_text(text, reply_markup=keyboard)

# --- Contact management ---
CONTACTS_FILE = "contacts.json"


# --- Contact management ---
CONTACTS_FILE = "contacts.json"

pending_addcontact = {}
pending_deletecontact = {}

# --- User tracking ---
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

def load_contacts():
    import json
    try:
        with open("contacts.json", "r", encoding="utf-8") as f:
            contacts = json.load(f)
            if not isinstance(contacts, list):
                contacts = []
    except Exception:
        contacts = []
    return contacts

def save_contacts(contacts):
    import json
    with open("contacts.json", "w", encoding="utf-8") as f:
        json.dump(contacts, f, indent=2)

async def addcontact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Use callback_query if message is None
    if hasattr(update, "message") and update.message:
        await update.message.reply_text("What is the contact's name?")
    elif hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text("What is the contact's name?")
    else:
        # Fallback: do nothing or log
        pass
    user_id = str(update.effective_user.id)
    pending_addcontact[user_id] = {"step": 1}

async def handle_addcontact_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in pending_addcontact:
        return False
    state = pending_addcontact[user_id]
    if state["step"] == 1:
        # Normalize name: strip spaces, lower case
        state["name"] = update.message.text.strip().replace(' ', '').lower()
        state["step"] = 2
        await update.message.reply_text("What is the contact's Telegram user ID?)")
        return True
    if state["step"] == 2:
        name = state["name"]
        try:
            telegram_user_id = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text("That doesn't look like a valid numeric user ID. Please enter the contact's Telegram user ID (a number).")
            return True
        contacts = load_contacts()
        if user_id not in contacts:
            contacts[user_id] = {}
        contacts[user_id][name] = telegram_user_id
        save_contacts(contacts)
        await update.message.reply_text(f"Contact '{name}' with user ID {telegram_user_id} added.")
        del pending_addcontact[user_id]
        return True
    return False

async def viewcontacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contacts = load_contacts()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Commands", callback_data="cmd_showcommands")]
    ])
    if not contacts:
        msg = "You have no contacts saved."
    else:
        msg = "Your contacts:\n" + "\n".join([f"{c.get('name', 'Unknown')}: user ID {c.get('telegram_id', 'N/A')}" for c in contacts])
    # If triggered by a message, reply; if by a button, edit the message
    if hasattr(update, "message") and update.message:
        await update.message.reply_text(msg, reply_markup=keyboard)
    elif hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=keyboard)

# --- Delete Contact Flow ---
async def deletecontact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contacts = load_contacts()
    if not contacts:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Commands", callback_data="cmd_showcommands")]
        ])
        if hasattr(update, "message") and update.message:
            await update.message.reply_text("You have no contacts to delete.", reply_markup=keyboard)
        elif hasattr(update, "callback_query") and update.callback_query:
            await update.callback_query.edit_message_text("You have no contacts to delete.", reply_markup=keyboard)
        return
    # Show contact names as buttons, callback data is index
    buttons = [[InlineKeyboardButton(c.get('name', 'Unknown'), callback_data=f"delete_contact_{i}")] for i, c in enumerate(contacts)]
    keyboard = InlineKeyboardMarkup(buttons)
    if hasattr(update, "message") and update.message:
        await update.message.reply_text("Select a contact to delete:", reply_markup=keyboard)
    elif hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text("Select a contact to delete:", reply_markup=keyboard)

async def handle_delete_contact_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("delete_contact_"):
        idx = int(data.split("delete_contact_")[1])
        contacts = load_contacts()
        if 0 <= idx < len(contacts):
            deleted = contacts.pop(idx)
            save_contacts(contacts)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Commands", callback_data="cmd_showcommands")]
            ])
            await query.edit_message_text(f"Contact '{deleted.get('name', 'Unknown')}' deleted.", reply_markup=keyboard)
        else:
            await query.edit_message_text("Contact not found.")

# --- Add missing global states and stubs to fix lint errors ---
pending_reminder = {}
pending_contact = {}

def save_contacts(contacts):
    import json
    with open("contacts.json", "w", encoding="utf-8") as f:
        json.dump(contacts, f, indent=2)

def load_contacts():
    import json
    try:
        with open("contacts.json", "r", encoding="utf-8") as f:
            contacts = json.load(f)
            if not isinstance(contacts, list):
                contacts = []
    except Exception:
        contacts = []
    return contacts

# Stubs for reminder flow functions if not defined
async def handle_set_reminder_flow(update, context):
    return False
async def reminder_callback_handler(update, context):
    pass
async def handle_add_contact_flow(update, context):
    return False
async def try_relay_message(update, context, user_input):
    return False

def main():
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
    import os
    BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    # Add your handlers here
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("reminders", reminders_command))
    app.add_handler(CommandHandler("commands", commands_command))
    app.add_handler(CommandHandler("addcontact", addcontact_command))
    app.add_handler(CommandHandler("viewcontacts", viewcontacts_command))
    app.add_handler(CommandHandler("deletecontact", deletecontact_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))
    print("Zoey Telegram Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
