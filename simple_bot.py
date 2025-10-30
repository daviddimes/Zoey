import os
import asyncio
import datetime
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Simple in-memory storage for reminders
reminders = []

# OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id
    
    try:
        # Ask AI if this is a reminder or chat
        intent_response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Respond with only 'REMINDER' if the user wants to set a reminder, or 'CHAT' for anything else."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=10
        )
        
        intent = intent_response.choices[0].message.content.strip().upper()
        
        if intent == 'REMINDER':
            # Parse reminder details
            reminder_response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "Extract reminder details as JSON: {\"text\": \"reminder text\", \"date\": \"today/tomorrow\", \"time\": \"HH:MM\"}. If no text, use 'Reminder'. If no date, use 'today'. If no time, use current time + 1 hour."
                    },
                    {"role": "user", "content": user_message}
                ],
                max_tokens=100
            )
            
            try:
                details = json.loads(reminder_response.choices[0].message.content.strip())
                
                # Create target datetime
                now = datetime.datetime.now()
                if details["date"].lower() == "tomorrow":
                    target_date = now.date() + datetime.timedelta(days=1)
                else:
                    target_date = now.date()
                
                try:
                    hour, minute = details["time"].split(":")
                    target_time = datetime.time(int(hour), int(minute))
                except:
                    # Default to 1 hour from now
                    future = now + datetime.timedelta(hours=1)
                    target_time = future.time()
                    target_date = future.date()
                
                target_datetime = datetime.datetime.combine(target_date, target_time)
                
                # If time has passed today, move to tomorrow
                if target_datetime <= now:
                    target_datetime += datetime.timedelta(days=1)
                
                # Store reminder
                reminders.append({
                    'user_id': user_id,
                    'text': details["text"],
                    'time': target_datetime
                })
                
                time_str = target_datetime.strftime("%B %d at %I:%M %p")
                response = f"✅ Reminder set: '{details['text']}' on {time_str}"
                
            except:
                response = "Sorry, I couldn't understand that reminder format."
        
        else:
            # Handle chat
            chat_response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Zoey, a helpful assistant. Keep responses brief and friendly."},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=100
            )
            response = chat_response.choices[0].message.content
    
    except Exception as e:
        print(f"Error: {e}")
        response = "Sorry, I had trouble with that request."
    
    await update.message.reply_text(response)

async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Check for due reminders and send them"""
    now = datetime.datetime.now()
    
    # Find due reminders
    due_reminders = []
    for reminder in reminders[:]:  # Copy list
        if reminder['time'] <= now:
            due_reminders.append(reminder)
            reminders.remove(reminder)
    
    # Send due reminders
    for reminder in due_reminders:
        try:
            await context.bot.send_message(
                chat_id=reminder['user_id'],
                text=f"⏰ Reminder: {reminder['text']}"
            )
            print(f"Sent reminder: {reminder['text']}")
        except Exception as e:
            print(f"Failed to send reminder: {e}")

def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()
    
    # Add message handler
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Add reminder checker job (every 30 seconds)
    app.job_queue.run_repeating(check_reminders, interval=30, first=10)
    
    print("🤖 Simple Zoey bot starting...")
    app.run_polling()

if __name__ == '__main__':
    main()