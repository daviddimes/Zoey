import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv

# Load environment variables before importing modules that need them
load_dotenv()

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from intents import (
    determine_intent,
    handle_reminder,
    handle_chat,
    handle_list_reminders,
    handle_edit_reminder,
    handle_delete_reminder,
)
from reminders import get_due_reminders, init_db

# Global application reference for sending reminders
app = None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id

    intent = await determine_intent(user_message)

    if intent == 'REMINDER':
        response = await handle_reminder(user_message, user_id)
    elif intent == 'LIST_REMINDERS':
        response = await handle_list_reminders(user_id)
    elif intent == 'EDIT_REMINDER':
        response = await handle_edit_reminder(user_message, user_id)
    elif intent == 'DELETE_REMINDER':
        response = await handle_delete_reminder(user_message, user_id)
    else:
        response = await handle_chat(user_message)

    await update.message.reply_text(response)

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Job that runs every 30 seconds to check for due reminders."""
    try:
        due_reminders = await get_due_reminders()

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


async def main():
    global app

    parser = argparse.ArgumentParser(description='Zoey Telegram bot')
    parser.add_argument('--polling', action='store_true', help='Run in polling mode locally')
    args = parser.parse_args()

    try:
        token = os.getenv('BOT_TOKEN')
        if not token:
            print('ERROR: BOT_TOKEN environment variable not found')
            return

        print('🤖 Zoey is starting up...')
        print(f'Token starts with: {token[:10]}...')

        await init_db()

        app = Application.builder().token(token).build()
        app.add_handler(MessageHandler(filters.TEXT, handle_message))
        app.job_queue.run_repeating(reminder_job, interval=30, first=10)

        if args.polling:
            print('✅ Reminder system active')
            print('✅ Starting polling mode...')
            await app.run_polling()
        else:
            webhook_url = os.getenv('WEBHOOK_URL') or f'https://zoey-9wkdiq.fly.dev/{token}'
            print('✅ Reminder system active')
            print('✅ Starting webhook server on 0.0.0.0:8080...')
            await app.run_webhook(
                listen='0.0.0.0',
                port=8080,
                webhook_url=webhook_url,
                url_path=token,
                bootstrap_retries=0,
                max_connections=40,
            )

    except Exception as e:
        print(f'FATAL ERROR: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
