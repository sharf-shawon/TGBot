# TGBot - OpenRouter Telegram Bot

A Telegram bot that integrates with OpenRouter AI models to provide chat capabilities with free AI models.

## Features

- 🔑 **API Key Management**: Securely store and manage OpenRouter API keys
- 🤖 **Free Model Selection**: Automatically fetches and displays available free models from OpenRouter
- 💬 **AI Chat**: Chat with selected AI models through Telegram
- ⚡ **Streaming Responses**: Messages update in real-time as AI generates responses
- 💾 **Persistent Storage**: All API keys, model selections, and chat history are saved locally
- 📝 **Chat History**: All conversations are saved in JSON format for training purposes
- 🔄 **Model Switching**: Change AI models at any time during conversations
- 🐳 **Docker Support**: Ready-to-deploy Docker configuration with volume persistence

## Prerequisites

- Python 3.13+
- UV package manager (or pip)
- Docker (optional, for containerized deployment)
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))
- OpenRouter API Key (get from [OpenRouter](https://openrouter.ai/keys))

## Installation

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd TGBot
```

2. Install dependencies:
```bash
uv sync
```

3. Create a `.env` file in the `src/` directory:
```bash
TG_BOT_TOKEN=your_telegram_bot_token_here
```

4. Run the bot:
```bash
uv run python src/main.py
```

### Docker Deployment

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

2. The bot will automatically create a `data/` directory for persistent storage

## Usage

### First Time Setup

1. Start a chat with your bot on Telegram
2. Send `/start` command
3. The bot will ask for your OpenRouter API key
4. Paste your API key (it will be validated)
5. The bot will show available free models
6. Select a model by sending its number
7. Start chatting!

### Commands

- `/start` - Initial setup or restart (asks for API key and model selection)
- `/help` - Show help message with available commands
- `/change_model` - Switch to a different AI model
- `/delete_api_key` - Remove your API key from the server
- `/cancel` - Cancel current operation

### Chat Flow

After setup, simply send any message to the bot and it will respond using your selected AI model. The bot maintains conversation context by keeping track of recent messages.

## Data Storage

All data is stored in the `data/` directory:

```
data/
├── users/          # User data (API keys, selected models)
│   └── {user_id}.json
└── chats/          # Chat history
    └── {user_id}.json
```

### User Data Format
```json
{
  "user_id": 123456789,
  "api_key": "sk-or-v1-...",
  "selected_model": "meta-llama/llama-3.3-70b-instruct:free",
  "created_at": "2026-02-15T10:30:00",
  "updated_at": "2026-02-15T10:35:00"
}
```

### Chat History Format
```json
{
  "user_id": 123456789,
  "messages": [
    {
      "role": "user",
      "content": "Hello!",
      "timestamp": "2026-02-15T10:35:00"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help you?",
      "model": "meta-llama/llama-3.3-70b-instruct:free",
      "timestamp": "2026-02-15T10:35:02"
    }
  ]
}
```

## Architecture

### Project Structure

```
TGBot/
├── src/
│   ├── main.py              # Main bot application
│   ├── core/
│   │   ├── config.py        # Configuration management
│   │   └── env.py           # Environment variable handling
│   └── services/
│       ├── openrouter.py    # OpenRouter API client
│       └── user_data.py     # User data management
├── data/                    # Persistent storage (gitignored)
├── docker-compose.yaml      # Docker Compose configuration
├── Dockerfile               # Docker image definition
└── pyproject.toml           # Project dependencies
```

### Services

#### UserDataManager (`services/user_data.py`)
- Manages user API keys
- Stores model selections
- Saves and retrieves chat history
- All data persisted in JSON files

#### OpenRouterClient (`services/openrouter.py`)
- Fetches available models from OpenRouter
- Filters free models
- Handles chat completion requests
- Validates API keys

## Security Notes

- ⚠️ API keys are stored in plain text in JSON files
- 🔒 The `data/` directory is excluded from version control
- 🐳 In Docker, ensure volume permissions are properly set
- 💡 Consider encrypting sensitive data for production use

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TG_BOT_TOKEN` | Telegram Bot Token | Yes | - |

## License

This program is dedicated to the public domain under the CC0 license.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

## Acknowledgments

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Powered by [OpenRouter](https://openrouter.ai/)
