import os
import datetime
import json
from openai import AsyncOpenAI
from reminders import add_reminder

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def determine_intent(user_message):
    """Use AI to determine what the user wants to do"""
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Classify intent. Respond with only REMINDER or CHAT.\n\nREMINDER = User wants to receive a notification later\nCHAT = Everything else (questions, statements, advice, conversation)\n\nExamples:\n'What's a good drink at Starbucks?' → CHAT\n'Recommend a book' → CHAT\n'I'm on PTO today' → CHAT\n'Tell me about yourself' → CHAT\n'What time is it' → CHAT\n'Remind me to call mom at 3pm' → REMINDER\n'Set a reminder for my meeting tomorrow' → REMINDER\n'Don't let me forget to buy milk' → REMINDER\n'Ping me in an hour' → REMINDER\n'Alert me when it's 5pm' → REMINDER"},
                {"role": "user", "content": user_message}
            ],
            max_tokens=10,
            temperature=0
        )
        intent = response.choices[0].message.content.strip().upper()
        return intent if intent in ['REMINDER', 'CHAT'] else 'CHAT'
    except:
        return 'CHAT'

async def parse_reminder_details(user_message):
    """Use AI to extract date, time, and reminder text from user message"""
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": """Extract reminder details from the user's message. Respond with JSON format:
{
  "reminder_text": "what to remind about (optional)",
  "date": "YYYY-MM-DD format or 'today' or 'tomorrow'",
  "time": "HH:MM format (24-hour)"
}

If no reminder text is specified, use "Reminder". If no date is specified, use "today". If no time is specified, use current time + 1 hour.

Examples:
"Remind me at 3pm tomorrow" -> {"reminder_text": "Reminder", "date": "tomorrow", "time": "15:00"}
"Call mom at 2:30" -> {"reminder_text": "Call mom", "date": "today", "time": "14:30"}"""
                },
                {"role": "user", "content": user_message}
            ],
            max_tokens=100
        )
        
        details = json.loads(response.choices[0].message.content.strip())
        return details
    except Exception as e:
        print(f"Error parsing reminder details: {e}")
        return None

def create_datetime_from_details(date_str, time_str):
    """Convert date and time strings to datetime object"""
    now = datetime.datetime.now()
    
    # Handle date
    if date_str.lower() == "today":
        target_date = now.date()
    elif date_str.lower() == "tomorrow":
        target_date = now.date() + datetime.timedelta(days=1)
    else:
        try:
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            target_date = now.date()  # Default to today
    
    # Handle time
    try:
        time_parts = time_str.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        target_time = datetime.time(hour, minute)
    except:
        # Default to 1 hour from now
        future_time = now + datetime.timedelta(hours=1)
        target_time = future_time.time()
    
    # Combine date and time
    target_datetime = datetime.datetime.combine(target_date, target_time)
    
    # If the time has already passed today, move to tomorrow
    if target_datetime <= now:
        target_datetime += datetime.timedelta(days=1)
    
    return target_datetime

async def handle_reminder(user_message, user_id):
    """Handle reminder requests"""
    try:
        # Parse reminder details using AI
        details = await parse_reminder_details(user_message)
        
        if not details:
            return "Sorry, I couldn't understand that reminder. Try something like 'Remind me to call mom at 3pm tomorrow'"
        
        # Create datetime from details
        target_datetime = create_datetime_from_details(details["date"], details["time"])
        
        # Add the reminder
        add_reminder(user_id, details["reminder_text"], target_datetime)
        
        # Format response
        time_str = target_datetime.strftime("%B %d at %I:%M %p")
        return f"✅ Reminder set: '{details['reminder_text']}' on {time_str}"
        
    except Exception as e:
        print(f"Error handling reminder: {e}")
        return "Sorry, I couldn't set that reminder. Try something like 'Remind me to call mom at 3pm tomorrow'"

async def handle_chat(user_message):
    """Handle regular chat requests"""
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Zoey, a helpful personal assistant. Keep responses brief and friendly."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content
    except:
        return 'Sorry, I had trouble understanding that.'