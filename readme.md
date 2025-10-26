# Zoey - AI Telegram Bot 🤖

An intelligent Telegram bot powered by OpenAI with smart intent classification and reminder functionality.

## 🌟 Features

- **AI-Powered Conversations**: Natural language processing using OpenAI GPT-3.5-turbo
- **Smart Intent Classification**: Automatically determines if users want to chat or set reminders
- **Reminder System**: AI extracts and stores reminders from natural language
- **Telegram Integration**: Seamless messaging through Telegram
- **Modular Architecture**: Clean, organized code structure
- **Environment-Based Configuration**: Secure API key management

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from @BotFather)
- OpenAI API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/daviddimes/zoey.git
   cd zoey
   ```

2. **Set up virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install python-telegram-bot openai python-dotenv
   ```

4. **Configure environment:**
   ```bash
   echo "BOT_TOKEN=your_telegram_bot_token" > .env
   ```

5. **Run the bot:**
   ```bash
   python messaging.py
   ```

## 🏗️ Project Structure

```
zoey/
├── messaging.py           # Main Telegram bot handler
├── intents.py            # AI intent classification system
├── reminders.py          # Reminder functionality
├── .env                  # Environment variables (API keys)
├── requirements.txt      # Python dependencies
├── venv/                # Virtual environment
└── README.md            # This file
```

## 💬 How It Works

### Intent Classification
Zoey uses AI to understand what users want:

- **REMINDER**: "Remind me to call mom", "Don't forget dentist appointment"
- **CHAT**: "How are you?", "What's the weather like?"

### Message Flow
1. User sends message to Telegram bot
2. `messaging.py` receives the message
3. `intents.py` classifies the intent using AI
4. Routes to appropriate handler:
   - **Reminder**: Extracts and stores reminder
   - **Chat**: Generates conversational response

## 🔧 Configuration

### Environment Variables (.env)
```bash
BOT_TOKEN=your_telegram_bot_token_from_botfather
```

### Getting API Keys

**Telegram Bot Token:**
1. Message @BotFather on Telegram
2. Send `/newbot` and follow prompts
3. Copy the bot token

**OpenAI API Key:**
- Visit https://platform.openai.com/api-keys
- Create new secret key
- Add to `intents.py` file

## 🎯 Usage Examples

### Setting Reminders
- "Remind me to buy groceries"
- "Don't forget the meeting at 3pm"
- "Remember to call John tomorrow"

### Chat Conversations
- "Hello, how are you?"
- "What's the weather like?"
- "Tell me a joke"
- "Help me with math"

## 🛠️ Development

### Adding New Intents
1. Update `determine_intent()` in `intents.py`
2. Create new handler function
3. Add routing in `messaging.py`

### Running in Development
```bash
# Activate virtual environment
source venv/bin/activate

# Run with logging
python messaging.py
```

### File Descriptions

**messaging.py**: Main entry point that handles Telegram messages and routes them based on AI-determined intent.

**intents.py**: Contains AI-powered intent classification and handlers for different types of user requests.

**reminders.py**: Simple reminder system (can be integrated with intents.py).

## 🐛 Troubleshooting

**ModuleNotFoundError:**
- Ensure virtual environment is activated: `source venv/bin/activate`
- Install missing packages: `pip install package_name`

**InvalidToken Error:**
- Check your bot token in `.env` file
- Get fresh token from @BotFather if needed

**Import Errors:**
- Ensure all required files exist in the same directory
- Check file names match import statements exactly

## 📈 Future Enhancements

- [ ] Persistent reminder storage (database)
- [ ] Scheduled reminder notifications
- [ ] Multi-user support
- [ ] Voice message processing
- [ ] Integration with calendar services
- [ ] Weather and news updates
- [ ] Custom user personalities

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- OpenAI for powerful language models
- Python Telegram Bot library
- The open-source community

---

**Built with ❤️ by David Dimes**