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
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   Create a `.env` file with your API keys:
   ```bash
   echo "BOT_TOKEN=your_telegram_bot_token" > .env
   echo "OPENAI_API_KEY=your_openai_api_key" >> .env
   ```

5. **Run the bot:**
   ```bash
   python messaging.py
   ```

## 🏗️ Project Structure

```
zoey/
├── messaging.py           # Main Telegram bot handler (webhook mode for production)
├── intents.py            # AI intent classification system
├── reminders.py          # Reminder storage and retrieval system
├── .env                  # Environment variables (API keys - not in git)
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration for deployment
├── fly.toml             # Fly.io deployment configuration
├── .venv/               # Virtual environment
└── readme.md            # This file
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
OPENAI_API_KEY=your_openai_api_key
```

### Getting API Keys

**Telegram Bot Token:**
1. Message @BotFather on Telegram
2. Send `/newbot` and follow prompts
3. Copy the bot token

**OpenAI API Key:**
1. Visit https://platform.openai.com/api-keys
2. Create new secret key
3. Add to `.env` file

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
source .venv/bin/activate  # or: source venv/bin/activate

# Run with logging
python messaging.py
```

Note: Development mode uses polling to fetch messages from Telegram. Production deployment uses webhooks.

### File Descriptions

**messaging.py**: Main entry point that handles Telegram messages and routes them based on AI-determined intent. Uses webhooks in production, polling in development.

**intents.py**: Contains AI-powered intent classification (REMINDER vs CHAT) and handlers for different types of user requests using OpenAI.

**reminders.py**: Reminder storage and retrieval system with SQLite database. Includes scheduled job to check for due reminders every 30 seconds.

## 🐛 Troubleshooting

**ModuleNotFoundError:**
- Ensure virtual environment is activated: `source .venv/bin/activate`
- Install missing packages: `pip install -r requirements.txt`

**InvalidToken Error:**
- Check your bot token in `.env` file
- Ensure BOTH `BOT_TOKEN` and `OPENAI_API_KEY` are set
- Get fresh token from @BotFather if needed

**Import Errors:**
- Ensure all required files exist in the same directory
- Check file names match import statements exactly

**Bot not responding:**
- Check that environment variables are correctly set in `.env`
- Verify the bot token is valid
- Ensure OpenAI API key has credits available

## 📈 Future Enhancements

- [x] Persistent reminder storage (SQLite database)
- [x] Scheduled reminder notifications (every 30 seconds)
- [x] Production deployment on Fly.io
- [ ] Multi-user support with user-specific settings
- [ ] Voice message processing
- [ ] Integration with calendar services
- [ ] Weather and news updates
- [ ] Custom user personalities
- [ ] Reminder timezone support
- [ ] Natural language date/time parsing improvements

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## � Common Git Commands

Essential Git commands for working with this repository:

### Check Repository Status
```bash
git status
```
Shows the current state of your working directory and staging area. Displays modified files, untracked files, and files ready to commit.

### Switch Branches
```bash
# Switch to an existing branch
git checkout branch-name

# Create and switch to a new branch
git checkout -b new-branch-name

# Switch back to main branch
git checkout main
```
Use `checkout` to switch between branches or create new ones.

### List All Branches
```bash
# List local branches
git branch

# List all branches (local and remote)
git branch -a

# List remote branches only
git branch -r
```
Shows available branches. The current branch is marked with an asterisk (*).

### Pull Latest Changes
```bash
# Pull from current branch
git pull

# Pull from specific branch
git pull origin main
```
Downloads changes from the remote repository and merges them into your current branch. Use before starting work to stay up-to-date.

### Fetch Remote Changes
```bash
# Fetch all branches
git fetch

# Fetch specific branch
git fetch origin main
```
Downloads changes from remote but doesn't merge them. Useful to see what's changed without affecting your work.

### Push Your Changes
```bash
# Push to current branch
git push

# Push to specific branch
git push origin branch-name

# Push and set upstream (first time)
git push -u origin branch-name
```
Uploads your local commits to the remote repository.

### Common Workflow
```bash
# 1. Check current status
git status

# 2. Pull latest changes
git pull

# 3. Create feature branch
git checkout -b my-feature

# 4. Make your changes, then stage them
git add .

# 5. Commit changes
git commit -m "Add new feature"

# 6. Push to remote
git push -u origin my-feature

# 7. Switch back to main when done
git checkout main
```

## �📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- OpenAI for powerful language models
- Python Telegram Bot library
- The open-source community

---

## 🚀 Deployment

### Deploying to Fly.io

Zoey is configured to run on Fly.io with webhook support for production deployment.

#### Prerequisites
- Fly.io account (sign up at https://fly.io)
- Fly CLI installed on your system

#### Install Fly CLI

**Linux/macOS:**
```bash
curl -L https://fly.io/install.sh | sh
```

After installation, add to your PATH:
```bash
echo 'export FLYCTL_INSTALL="/home/YOUR_USERNAME/.fly"' >> ~/.bashrc
echo 'export PATH="$FLYCTL_INSTALL/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Verify installation:**
```bash
fly version
```

#### Setting Up Environment Variables

1. **Log in to Fly.io:**
   ```bash
   fly auth login
   ```

2. **Set environment secrets** (these are encrypted and secure):
   ```bash
   fly secrets set BOT_TOKEN=your_telegram_bot_token
   fly secrets set OPENAI_API_KEY=your_openai_api_key
   ```

3. **Verify secrets are set:**
   ```bash
   fly secrets list
   ```

#### Deploy the Application

1. **First-time deployment** (if not already initialized):
   ```bash
   fly launch
   ```
   - Follow the prompts to choose app name and region
   - Choose "No" for databases and Redis
   - The `fly.toml` configuration file will be created

2. **Deploy updates:**
   ```bash
   fly deploy
   ```

3. **Monitor the deployment:**
   ```bash
   fly logs
   ```

#### Verify Deployment

Check that your bot is running:
```bash
fly status
```

View real-time logs:
```bash
fly logs -f
```

#### Important Notes

- **Webhooks vs Polling**: The production deployment uses webhooks instead of polling, which is more efficient and required by Fly.io
- **Port Configuration**: The app listens on `0.0.0.0:8080` as required by Fly.io
- **Auto-scaling**: Fly.io will automatically start/stop machines based on traffic to save costs
- **Memory**: The app is configured with 256MB RAM (adjustable in `fly.toml`)

#### Troubleshooting Deployment

**Connection refused errors:**
- Ensure the app is listening on `0.0.0.0:8080`
- Check that `python-telegram-bot[webhooks,job-queue]` is in `requirements.txt`

**Environment variable issues:**
```bash
# Check current secrets
fly secrets list

# Update a secret
fly secrets set BOT_TOKEN=new_token
```

**View detailed logs:**
```bash
fly logs --app your-app-name
```

**Restart the application:**
```bash
fly apps restart your-app-name
```

#### Updating the Bot

1. Make your code changes locally
2. Test locally if possible
3. Deploy updates:
   ```bash
   fly deploy
   ```

The deployment typically takes 30-60 seconds and will automatically update your running bot.

---

**Built with ❤️ by David Dimes**