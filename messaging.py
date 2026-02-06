import os
import asyncio
from dotenv import load_dotenv

# Load environment variables before importing modules that need them
load_dotenv()

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from intents import determine_intent, handle_reminder, handle_chat
from reminders import get_due_reminders

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
    
    try:
        token = os.getenv("BOT_TOKEN")
        if not token:
            print("ERROR: BOT_TOKEN environment variable not found")
            return
            
        print("🤖 Zoey is starting up...")
        print(f"Token starts with: {token[:10]}...")
        
        # Build application - run_webhook will create necessary components
        app = Application.builder().token(token).build()
        app.add_handler(MessageHandler(filters.TEXT, handle_message))
        
        # Add the reminder checking job - run_webhook will initialize job_queue
        app.job_queue.run_repeating(reminder_job, interval=30, first=10)
        
        print("✅ Reminder system active")
        print("✅ Starting webhook server on 0.0.0.0:8080...")
        
        # Use webhooks for Fly.io deployment
        # run_webhook handles initialization internally
        app.run_webhook(
            listen="0.0.0.0",
            port=8080,
            webhook_url=f"https://zoey-9wkdiq.fly.dev/{token}",
            url_path=token,
            secret_token=None,
            cert=None,
            key=None,
            bootstrap_retries=0,
            max_connections=40,
            allowed_updates=None,
            ip_address=None,
            drop_pending_updates=None
        )
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()