import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from intents import determine_intent, handle_reminder, handle_chat

load_dotenv()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Determine what the user wants
    intent = await determine_intent(user_message)
    
    if intent == 'REMINDER':
        response = await handle_reminder(user_message)
    else:  # CHAT
        response = await handle_chat(user_message)
    
    await update.message.reply_text(response)

def main():
    token = os.getenv("BOT_TOKEN")
    application = Application.builder().token(token).build()
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()