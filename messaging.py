import argparse
import os

from dotenv import load_dotenv

# Load environment variables before importing modules that need them
load_dotenv()

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from health import (
    build_google_health_auth_url,
    build_health_dashboard,
    is_health_connected,
    fetch_health_metrics,
    start_health_callback_server,
)
from intents import (
    determine_intent,
    handle_chat,
    handle_delete_reminder,
    handle_edit_reminder,
    handle_list_reminders,
    handle_reminder,
)
from reminders import get_due_reminders, init_db

# Global application reference for sending reminders
app = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the main welcome message with the Health button."""
    keyboard = [[InlineKeyboardButton("Health", callback_data="health")]]
    await update.message.reply_text(
        "Hello! I can help with reminders and your health dashboard.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_health_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Health button and route the user to login or dashboard."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_health_connected(user_id):
        auth_url = build_google_health_auth_url(user_id)
        keyboard = [[InlineKeyboardButton("Connect Google Health", url=auth_url)]]
        message = (
            "To view your health stats, connect your Google Health account first.\n\n"
            "Tap the button below to continue."
        )
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    metrics = fetch_health_metrics(user_id)
    await query.edit_message_text(build_health_dashboard(metrics))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id

    normalized_message = (user_message or "").strip().lower()
    if normalized_message in {"health", "show health", "health dashboard", "dashboard"}:
        keyboard = [[InlineKeyboardButton("Health", callback_data="health")]]
        await update.message.reply_text(
            "Here is your health dashboard shortcut.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

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
                    text=f"⏰ Reminder: {reminder_text}",
                )
                print(f"Sent reminder to user {user_id}: {reminder_text}")
            except Exception as exc:
                print(f"Failed to send reminder to user {user_id}: {exc}")

    except Exception as exc:
        print(f"Error in reminder job: {exc}")


async def post_init(application: Application) -> None:
    """Initialize the database when the application starts."""
    print('Initializing database...')
    await init_db()
    print('Database initialized.')


def main():
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

        print('Building Telegram application...')
        app = Application.builder().token(token).post_init(post_init).build()
        try:
            start_health_callback_server(bot=getattr(app, 'bot', None))
        except Exception as exc:
            print(f'Health callback server startup warning: {exc}')
        app.add_handler(CommandHandler('start', start_command))
        app.add_handler(CallbackQueryHandler(handle_health_button, pattern='^health$'))
        app.add_handler(MessageHandler(filters.TEXT, handle_message))
        app.job_queue.run_repeating(reminder_job, interval=30, first=60)
        print('Application built and handlers added.')

        if args.polling:
            print('✅ Reminder system active')
            print('✅ Starting polling mode...')
            app.run_polling()
        else:
            webhook_url = os.getenv('WEBHOOK_URL') or f'https://zoey-9wkdiq.fly.dev/{token}'
            print(f'✅ Reminder system active')
            print(f'✅ Webhook URL: {webhook_url}')
            print(f'✅ URL path: {token}')
            print('✅ Starting webhook server on 0.0.0.0:8080...')
            app.run_webhook(
                listen='0.0.0.0',
                port=8080,
                webhook_url=webhook_url,
                url_path=token,
                bootstrap_retries=0,
                max_connections=40,
            )

    except Exception as exc:
        print(f'FATAL ERROR: {exc}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
