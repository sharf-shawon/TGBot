# Natural Language to SQL Telegram Bot

A sophisticated Telegram bot that converts natural language questions into SQL queries for PostgreSQL databases using LangChain and OpenRouter.

## Features

- 🤖 **Natural Language Processing**: Ask questions in plain English (or any language)
- 🔒 **Safe Query Execution**: Read-only access with comprehensive SQL filtering
- 🧠 **Smart SQL Generation**: Uses LangChain with OpenRouter LLMs
- 🎯 **Multiple Free AI Models**: Choose from all available OpenRouter free models
- 🔢 **Easy Model Selection**: Select models by number from a dynamic list
- ⚙️ **Per-User Model Customization**: Each user can select their preferred LLM model
- 🔄 **Schema Caching**: Automatic database schema detection and caching
- 🛡️ **Robust Error Handling**: Automatic retry and query improvement on errors
- 👥 **Access Control**: Admin-managed user permissions with easy-to-use commands

## Architecture

### Components

1. **Database Service** (`services/database.py`)
   - PostgreSQL connection management using psycopg2
   - Automatic schema fetching and caching
   - Safe query execution with error handling
   - Schema refresh functionality

2. **SQL Filter** (`services/sql_filter.py`)
   - Validates queries for dangerous keywords (INSERT, UPDATE, DELETE, DROP, etc.)
   - Detects SQL injection attempts and multiple statements
   - Enforces read-only operations (SELECT only)
   - Automatically adds LIMIT clauses for safety

3. **LLM Service** (`services/llm_service.py`)
   - Integrates with OpenRouter API via LangChain
   - Generates SQL queries from natural language using Claude/Gemini models
   - Converts query results back to natural language explanations
   - Improves queries based on error feedback (automatic retry)
   - Customizable model selection per user

4. **OpenRouter Models Service** (`services/openrouter_models.py`)
   - Fetches available models from OpenRouter API using httpx
   - Filters completely free models (zero cost for prompts and completions)
   - 24-hour caching for performance optimization
   - Provides formatted model lists with pagination support

5. **Query Processor** (`services/query_processor.py`)
   - Orchestrates the complete NL → SQL → Results → NL flow
   - Handles retries and automatic error recovery
   - Integrates all services for seamless query processing

6. **User State Manager** (`services/user_state.py`)
   - Stores user API keys persistently in local files
   - Manages per-user model preferences
   - Provides effective API key/model resolution (user override → global default)
   - File-based storage in DATA_DIR

7. **Access Control** (`services/access_control.py`)
   - Role-based access control (Admin and User roles)
   - Manages admin and user permissions
   - Stores access lists persistently in local files
   - Admin commands for user/admin management

## Setup

### Prerequisites

- Python 3.13 or higher
- PostgreSQL database (tested with PostgreSQL 17)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenRouter API Key (optional global key, or users provide their own)
- [uv package manager](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/sharf-shawon/TGBot.git
cd TGBot
```

2. Install uv package manager (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Copy the example environment file:
```bash
cp .env.example src/.env
```

4. Edit `src/.env` with your configuration:
```env
# Required - Telegram Bot Configuration
TG_BOT_TOKEN=your_telegram_bot_token
TG_BOT_NAME=YourBotName
TG_BOT_USERNAME=your_bot_username
TG_BOT_OWNER_ID=your_telegram_user_id

# Required - Admin Configuration
ADMIN_USER_IDS=123456789

# Required - Database Connection
POSTGRES_URL=postgresql://user:password@host:port/database

# Optional - Global API Key Configuration
# If set, users won't need to provide their own API key
# OPENROUTER_API_KEY=your_openrouter_api_key
# OPENROUTER_MODEL=google/gemini-flash-1.5:free

# Optional - Data Directory
# DATA_DIR=./data
```

5. Install dependencies:
```bash
uv sync
```

This will install:
- `python-telegram-bot` (>=22.6) - Telegram Bot API wrapper
- `langchain` (>=0.3.19) - LLM framework
- `langchain-openai` (>=0.2.14) - OpenAI/OpenRouter integration
- `psycopg2-binary` (>=2.9.10) - PostgreSQL adapter
- `sqlparse` (>=0.5.3) - SQL parser and formatter
- `httpx` (>=0.28.1) - Async HTTP client for OpenRouter API
- `python-dotenv` (>=1.2.1) - Environment variable management

### Running Locally

Run with auto-reload (development):
```bash
uv run src/main.py --watch
```

Or run normally:
```bash
uv run src/main.py
```

### Running with Docker

1. Create a `.env` file in the project root:
```env
# Required - Telegram Bot Configuration
TG_BOT_TOKEN=your_telegram_bot_token
TG_BOT_NAME=YourBotName
TG_BOT_USERNAME=your_bot_username
TG_BOT_OWNER_ID=your_telegram_user_id

# Required - Database and Admin
POSTGRES_URL=postgresql://user:password@host:port/database
ADMIN_USER_IDS=123456789

# Optional - Global API Key (recommended for team deployments)
# OPENROUTER_API_KEY=your_openrouter_api_key
# OPENROUTER_MODEL=google/gemini-flash-1.5:free
```

2. Build and run:
```bash
docker-compose up --build -d
```

3. View logs:
```bash
docker-compose logs -f tgbot
```

4. Stop the bot:
```bash
docker-compose down
```

5. Rebuild after code changes:
```bash
docker-compose up --build -d
```

## Usage

### Access Control

The bot has built-in access control to restrict usage to authorized users only.

#### Initial Setup

1. Set admin user IDs in `src/.env`:
```env
ADMIN_USER_IDS=123456789,987654321
```

2. Admins can automatically use all bot features
3. Other users need to be added by an admin

#### Getting Your User ID

Any user can use `/whoami` to get their Telegram user ID, which they can share with an admin to request access.

### Bot Commands

**General Commands:**
- `/start` - Initialize bot and set up OpenRouter API key
- `/help` - Show help message with examples
- `/whoami` - Show your user ID and access status
- `/config` - Update OpenRouter API key
- `/stats` - Show current settings and status
- `/models [page]` - Fetch and list all available free OpenRouter models (with pagination)
- `/set_model <number>` - Change model by number (e.g., `/set_model 1`)
- `/set_model <model_id>` - Change model by ID (e.g., `/set_model google/gemini-flash-1.5:free`)
- `/reset_model` - Reset to default model
- `/refresh` - Refresh database schema cache
- `/cancel` - Cancel current operation

**Admin Commands:**
- `/add_user <user_id>` - Add a user to the allowed list
- `/remove_user <user_id>` - Remove a user from the allowed list
- `/list_users` - Show all admins and allowed users
- `/add_admin <user_id>` - Promote a user to admin
- `/remove_admin <user_id>` - Remove admin status from a user

### Example Queries

Once you've set up your API key with `/start`, you can ask questions like:

- "Show me all users"
- "How many orders were placed today?"
- "What are the top 10 products by revenue?"
- "List all customers from New York"
- "Find users who registered in the last week"
- "What's the average order value?"

### Customizing Your AI Model

The bot dynamically fetches all free models from OpenRouter and lets you choose easily:

**View Available Models:**
```
/models
/models 2
```
This fetches and displays all free models from OpenRouter with numbers for easy selection.
Models are shown 15 per page. Use `/models <page>` to navigate between pages.

**Change Your Model (by number):**
```
/set_model 1
```
Select any model by its number from the `/models` list.

**Change Your Model (by ID):**
```
/set_model google/gemini-flash-1.5:free
```
You can also use the full model ID directly.

**Reset to Default:**
```
/reset_model
```

**Check Current Model:**
Use `/stats` or `/whoami` to see which model you're currently using.

**Note:** The bot automatically fetches the latest free models from OpenRouter, so you'll always have access to the newest options!

### Query Flow

1. User sends a natural language question
2. Bot validates it's a database query intent
3. LLM converts question to SQL query
4. SQL filter validates the query (no dangerous operations)
5. Query executed on PostgreSQL database
6. Results converted back to natural language
7. User receives explanation and formatted results

## Security Features

### SQL Filtering

The bot implements comprehensive SQL filtering to prevent dangerous operations:

- **Forbidden Keywords**: INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, etc.
- **Pattern Detection**: Multiple statements, SQL injection attempts
- **Read-Only Enforcement**: Only SELECT queries allowed
- **Automatic LIMIT**: Adds LIMIT clause if missing

### Data Protection

- User API keys stored locally (never in database)
- Database user should have read-only permissions
- No data modifications possible through bot
- All user data stored in Docker volumes (not in database)
- Access control prevents unauthorized usage

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TG_BOT_TOKEN` | Telegram bot token from BotFather | Yes | - |
| `TG_BOT_NAME` | Display name of your bot | No | Bot name from BotFather |
| `TG_BOT_USERNAME` | Username of your bot (without @) | No | Bot username from BotFather |
| `TG_BOT_OWNER_ID` | Your Telegram user ID | No | First admin ID |
| `POSTGRES_URL` | PostgreSQL connection URL | Yes | - |
| `ADMIN_USER_IDS` | Comma-separated admin user IDs | Yes | - |
| `OPENROUTER_API_KEY` | Global OpenRouter API key | No | None (users provide own) |
| `OPENROUTER_MODEL` | Default OpenRouter model | No | First free model from API |
| `DATA_DIR` | Directory for persistent storage | No | `./data` (local), `/app/data` (Docker) |

### API Key Configuration

The bot supports two modes for OpenRouter API key management:

**1. Per-User API Keys (Default)**
- Each user provides their own OpenRouter API key via `/start`
- Users have full control over their API usage and costs
- Best for multi-tenant deployments

**2. Global API Key (Optional)**
- Admin sets `OPENROUTER_API_KEY` in environment variables
- All users share the same API key
- Users can still override with personal keys via `/config`
- Best for single-team or controlled deployments

**Priority Order:**
1. User's personal API key (if set via `/config`)
2. Global API key (if set in environment)
3. No key available (bot prompts user to set one)

### Model Configuration

**Default Model:**
The bot automatically uses the first free model available from OpenRouter. You can override this in environment variables:
```env
OPENROUTER_MODEL=google/gemini-flash-1.5:free
```

**Per-User Model Override:**
Users can set their preferred model via `/set_model <number>` or `/set_model <model_id>`, which takes precedence over the default.

**Dynamic Model List:**
- The bot fetches all free models from OpenRouter API in real-time
- Models are cached for 24 hours for performance
- Use `/models [page]` to see the latest available free models
- Models are displayed 15 per page for easy browsing
- Select models easily by number: `/set_model 1`

**Model Management Commands:**
- `/models [page]` - View all free models with numbers (paginated)
- `/set_model <number>` - Set model by number (e.g., `/set_model 1`)
- `/set_model <model_id>` - Set model by ID (e.g., `/set_model google/gemini-flash-1.5:free`)
- `/reset_model` - Return to default model

### Database Requirements

- **PostgreSQL**: Version 17 recommended (compatible with most PostgreSQL versions)
- **User Permissions**: Read-only user strongly recommended for security
- **Network Access**: Bot must be able to connect to the database (check firewall rules)
- **Connection Format**: `postgresql://username:password@host:port/database`
- **Schema Access**: User must have SELECT permissions on relevant schemas and tables

### Docker Volumes

- `tgbot-data`: Stores user API keys and preferences

## Development

### Project Structure

```
TGBot/
├── src/
│   ├── main.py                    # Bot entry point with command handlers
│   ├── .env                       # Environment configuration (create from .env.example)
│   ├── core/
│   │   ├── config.py             # Configuration loader
│   │   └── env.py                # Environment variable utilities
│   └── services/
│       ├── access_control.py     # User access management
│       ├── database.py           # PostgreSQL service
│       ├── llm_service.py        # LangChain + OpenRouter integration
│       ├── openrouter_models.py  # OpenRouter API model fetching
│       ├── query_processor.py    # Query orchestration
│       ├── sql_filter.py         # SQL security validation
│       └── user_state.py         # User preferences & API keys
├── data/                          # Persistent data (created at runtime)
│   ├── chats/                    # Chat-specific data
│   └── users/                    # User API keys and preferences
├── .env.example                   # Example environment file
├── docker-compose.yaml            # Docker composition
├── Dockerfile                     # Docker image (Python 3.13-slim)
├── pyproject.toml                 # Python dependencies (uv)
├── uv.lock                        # Dependency lock file
└── README.md                      # This file
```

### Adding New Features

1. **New LLM Models**: 
   - Models are fetched dynamically from OpenRouter API
   - Update `OPENROUTER_MODEL` in `.env` to change default
   - Modify `openrouter_models.py` to adjust filtering criteria

2. **Custom SQL Filters**: 
   - Add patterns to `SQLFilter.FORBIDDEN_KEYWORDS` in `services/sql_filter.py`
   - Add regex patterns to `DANGEROUS_PATTERNS` for advanced filtering

3. **New Bot Commands**: 
   - Add command handlers in `main.py`
   - Register commands in the application builder
   - Update help text in `/help` command

4. **Custom LLM Prompts**:
   - Modify prompt templates in `services/llm_service.py`
   - Adjust temperature and model parameters as needed

### Testing

Test database connection:
```python
from services.database import DatabaseService
db = DatabaseService("postgresql://user:pass@host/db")
db.connect()
schema = db.fetch_full_schema()
print(schema)
```

Test SQL filtering:
```python
from services.sql_filter import SQLFilter
is_valid, error = SQLFilter.validate_query("SELECT * FROM users")
print(f"Valid: {is_valid}, Error: {error}")
```

## Troubleshooting

### Bot not connecting to database

- Check `POSTGRES_URL` format
- Ensure database is accessible from bot
- Verify user has SELECT permissions

### Query generation fails

- Check OpenRouter API key is valid
- Verify database schema is cached (`/refresh`)
- Review bot logs for LLM errors

### Docker volume issues

```bash
# Backup data
docker cp <container_id>:/app/data ./data_backup

# Recreate volume
docker-compose down -v
docker-compose up -d
```

## Key Features Summary

✅ **Dynamic Model Management** - Fetches latest free models from OpenRouter API
✅ **Pagination Support** - Browse 15 models per page with easy navigation
✅ **Number-Based Selection** - Quick model selection using numbers (e.g., `/set_model 1`)
✅ **24-Hour Caching** - Efficient model list caching for better performance
✅ **Per-User Customization** - Each user can have their own preferred model
✅ **Global API Key Support** - Optional shared API key for team deployments
✅ **Comprehensive Security** - SQL injection prevention and read-only enforcement
✅ **Admin Controls** - User access management with role-based permissions
✅ **Docker Support** - Easy deployment with Docker Compose
✅ **Auto-Retry Logic** - Automatic query improvement on errors

## Technology Stack

- **Language**: Python 3.13+
- **Bot Framework**: python-telegram-bot (async)
- **LLM Framework**: LangChain + LangChain-OpenAI
- **Database**: PostgreSQL with psycopg2
- **HTTP Client**: httpx (async)
- **Package Manager**: uv
- **Deployment**: Docker + Docker Compose
- **AI Provider**: OpenRouter (supports Claude, Gemini, and more)

## Performance & Optimization

- **Schema Caching**: Database schema is cached to reduce repeated queries
- **Model Caching**: Free models list is cached for 24 hours
- **User State**: Local file-based storage for fast access
- **Connection Pooling**: Efficient database connection management
- **Async Operations**: Non-blocking HTTP requests with httpx

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Guidelines

1. Follow PEP 8 style guidelines (enforced by Ruff)
2. Add type hints to all functions
3. Write descriptive commit messages
4. Test changes with Docker before submitting
5. Update documentation for new features

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

## Changelog

### Version 0.1.0 (Current)
- ✨ Dynamic model fetching from OpenRouter API
- ✨ Pagination support for model lists (15 per page)
- ✨ Number-based model selection
- ✨ Per-user model and API key preferences
- ✨ 24-hour model caching
- ✨ Comprehensive access control system
- ✨ SQL injection prevention
- ✨ Docker deployment support
- ✨ Automatic query retry and improvement
