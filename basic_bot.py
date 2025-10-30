import os
import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Simple in-memory storage for reminders
reminders = []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    user_id = update.effective_user.id
    
    try:
        # Simple keyword-based intent detection
        if any(word in user_message for word in ['remind', 'reminder', 'alert', 'notify']):
            # Very simple time parsing
            now = datetime.datetime.now()
            target_time = now + datetime.timedelta(minutes=5)  # Default: 5 minutes from now
            
            # Extract reminder text (everything after "remind me to" or similar)
            reminder_text = "Reminder"
            if "remind me to" in user_message:
                reminder_text = user_message.split("remind me to", 1)[1].strip()
            elif "remind me" in user_message:
                reminder_text = user_message.split("remind me", 1)[1].strip()
            
            if not reminder_text or reminder_text == "":
                reminder_text = "Reminder"
            
            # Store reminder
            reminders.append({
                'user_id': user_id,
                'text': reminder_text,
                'time': target_time
            })
            
            response = f"✅ I'll remind you '{reminder_text}' in 5 minutes!"
        
        else:
            # Simple chat response
            if "hello" in user_message or "hi" in user_message:
                response = "Hello! I'm Zoey. You can ask me to remind you of things!"
            else:
                response = "I'm Zoey! Try saying 'remind me to call mom' or just say hello!"
    
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
    if not token:
        print("ERROR: BOT_TOKEN not found in environment variables")
        return
        
    print("🤖 Starting basic Zoey bot...")
    print(f"Bot token starts with: {token[:10]}...")
    
    app = Application.builder().token(token).build()
    
    # Add message handler
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Add reminder checker job (every 30 seconds)
    app.job_queue.run_repeating(check_reminders, interval=30, first=10)
    
    print("✅ Bot configured, starting polling...")
    app.run_polling()

if __name__ == '__main__':
    main()