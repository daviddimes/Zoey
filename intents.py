import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Store reminders
reminders = []

async def determine_intent(user_message):
    """Use AI to determine what the user wants to do"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an intent classifier. Respond with ONLY one word: 'REMINDER' if the user wants to set a reminder or remember something, or 'CHAT' if they want to have a conversation or ask questions."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=10
        )
        intent = response.choices[0].message.content.strip().upper()
        return intent if intent in ['REMINDER', 'CHAT'] else 'CHAT'
    except:
        return 'CHAT'

async def handle_reminder(user_message):
    """Handle reminder requests"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Extract the reminder from this message. Respond with just the reminder text, nothing else."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=50
        )
        reminder_text = response.choices[0].message.content.strip()
        reminders.append(reminder_text)
        return f"✅ Reminder set: {reminder_text}"
    except:
        return "Sorry, I couldn't set that reminder."

async def handle_chat(user_message):
    """Handle regular chat requests"""
    try:
        response = client.chat.completions.create(
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