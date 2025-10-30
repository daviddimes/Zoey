import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from intents import determine_intent, handle_reminder, handle_chat
from reminders import get_due_reminders

load_dotenv()

# Global application reference for sending reminders
app = None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id
    
    # Determine what the user wants
    intent = await determine_intent(user_message)
    
    if intent == 'REMINDER':
        response = await handle_reminder(user_message, user_id)
    else:  # CHAT
        response = await handle_chat(user_message)
    
    await update.message.reply_text(response)

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Job that runs every 30 seconds to check for due reminders"""
    try:
        due_reminders = get_due_reminders()
        
        for user_id, reminder_text in due_reminders:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ Reminder: {reminder_text}"
                )
                print(f"Sent reminder to user {user_id}: {reminder_text}")
            except Exception as e:
                print(f"Failed to send reminder to user {user_id}: {e}")
                
    except Exception as e:
        print(f"Error in reminder job: {e}")

def main():
    global app
    
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Add the reminder checking job to run every 30 seconds
    app.job_queue.run_repeating(reminder_job, interval=30, first=10)
    
    print("🤖 Zoey is starting up...")
    print("✅ Reminder system active")
    
    app.run_polling()

if __name__ == '__main__':
    main()