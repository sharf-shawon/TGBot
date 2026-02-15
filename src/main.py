#!/usr/bin/env python
# pylint: disable=unused-argument
"""
Natural Language to SQL Telegram Bot.

This bot allows users to query PostgreSQL databases using natural language.
It uses LangChain and OpenRouter to convert questions to SQL queries and
results back to natural language.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from core.config import (
    ADMIN_USER_IDS,
    DATA_DIR,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    POSTGRES_URL,
    TG_BOT_TOKEN,
)
from services.access_control import AccessControl
from services.database import DatabaseService
from services.openrouter_models import get_models_service
from services.query_processor import QueryProcessor
from services.user_state import UserStateManager

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_API_KEY = 1

# Global instances
user_manager: Optional[UserStateManager] = None
database: Optional[DatabaseService] = None
access_control: Optional[AccessControl] = None

# Cache for model number mappings (user_id -> {number -> model_id})
user_model_mappings: Dict[int, Dict[int, str]] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command - check if user has API key."""
    user = update.effective_user
    user_id = user.id

    # Check if user is allowed
    if not access_control.is_allowed(user_id):
        await update.message.reply_text(
            "🚫 Access Denied\n\n"
            "You are not authorized to use this bot.\n\n"
            f"Your user ID: `{user_id}`\n\n"
            "Please contact an administrator to request access.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    logger.info(f"User {user_id} started the bot")

    # Check if user has API key or if global API key is configured
    has_user_key = user_manager.has_api_key(user_id)
    has_global_key = OPENROUTER_API_KEY is not None
    
    if has_user_key or has_global_key:
        is_admin = access_control.is_admin(user_id)
        admin_note = " You have admin privileges." if is_admin else ""
        
        # Determine API key source for display
        if has_user_key:
            api_note = "Using your personal OpenRouter API key."
        else:
            api_note = "Using global OpenRouter API key. You can set your own with /config if desired."
        
        await update.message.reply_text(
            f"👋 Welcome back, {user.first_name}!{admin_note}\n\n"
            "💬 Ask me questions about your database in natural language.\n\n"
            f"🔑 {api_note}\n\n"
            "Quick Commands:\n"
            "• /help - Complete command list and examples\n"
            "• /models - View available free AI models\n"
            "• /stats - Your settings\n"
            "• /refresh - Reload database schema\n\n"
            "Just type your question to get started!"
        )
        return ConversationHandler.END

    # User doesn't have API key and no global key configured
    await update.message.reply_text(
        f"👋 Hello, {user.first_name}!\n\n"
        "🤖 I'm a **Natural Language to SQL Bot**\n\n"
        "I can help you query your PostgreSQL database using plain language. "
        "Just ask questions like 'Show me all users' or 'How many orders today?'\n\n"
        "🔑 **Setup Required:**\n"
        "Please send me your OpenRouter API key to get started.\n"
        "Get your free key at: https://openrouter.ai/keys\n\n"
        "💡 Your API key is stored securely and only used for your queries.\n\n"
        "Send /cancel to abort.",
        parse_mode="Markdown"
    )
    return WAITING_FOR_API_KEY


async def receive_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and store the OpenRouter API key."""
    user_id = update.effective_user.id
    api_key = update.message.text.strip()

    # Basic validation
    if len(api_key) < 20 or " " in api_key:
        await update.message.reply_text(
            "❌ That doesn't look like a valid API key.\n"
            "Please try again or send /cancel to abort."
        )
        return WAITING_FOR_API_KEY

    # Store the API key
    user_manager.set_api_key(user_id, api_key)

    await update.message.reply_text(
        "✅ API key saved successfully!\n\n"
        "🎉 You're all set! You can now ask me questions about your database.\n\n"
        "**Try these examples:**\n"
        "• Show me all users\n"
        "• How many orders were placed today?\n"
        "• What are the top 10 products by revenue?\n"
        "• List customers from New York\n\n"
        "**Useful Commands:**\n"
        "• /help - See all commands and features\n"
        "• /models - View available free AI models\n"
        "• /set_model - Choose your preferred model (by number!)\n"
        "• /stats - View your settings\n\n"
        "💡 Tip: Try different models to find what works best for you!",
        parse_mode="Markdown"
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text(
        "Operation cancelled. Send /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    user_id = update.effective_user.id
    is_admin = access_control.is_admin(user_id)
    
    help_text = """
🤖 **Natural Language to SQL Bot**

**What I Do:**
I convert your questions into SQL queries, execute them safely on your PostgreSQL database, and explain the results in natural language.

━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📝 How to Use:**

Simply type your question as you would ask a person:

• "Show me all users"
• "How many orders were placed yesterday?"
• "What are the top 5 products by sales?"
• "List customers from New York"
• "Find all orders over $100"
• "What's the average order value by month?"

I'll understand your intent and query the database for you!

━━━━━━━━━━━━━━━━━━━━━━━━━━━

**⚙️ General Commands:**

/start - Initialize bot and setup API key
/help - Show this help message
/whoami - Display your user ID and access level
/config - Update your OpenRouter API key
/stats - View your current settings
/models - Fetch available free models from OpenRouter (with pagination)
/set_model - Change your preferred model (use numbers!)
/reset_model - Return to default model
/refresh - Reload database schema from server
/cancel - Cancel ongoing operation

━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🎯 Model Customization:**

**View Available Models:**
Use `/models` or `/models <page>` to see free OpenRouter models.
Models are displayed with numbers for easy selection (15 per page).

**Change Your Model:**
`/set_model <number>` or `/set_model <model_id>`

Examples:
• `/set_model 1` - Select first model from the list
• `/set_model 5` - Select fifth model  
• `/set_model google/gemini-flash-1.5:free` - Select by full ID

**Navigate Pages:**
• `/models` - Show first page
• `/models 2` - Show second page
• `/models 3` - Show third page

**Reset to Default:**
Use `/reset_model` to return to the default model.

**Current Model:**
Check `/stats` or `/whoami` to see which model you're using.

💡 Models are fetched directly from OpenRouter, so you always have access to the latest free options!
"""
    
    if is_admin:
        help_text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━

**👑 Admin Commands:**

**User Management:**
/add_user `<user_id>` - Grant access to a user
/remove_user `<user_id>` - Revoke user access
/list_users - View all admins and users

**Admin Management:**
/add_admin `<user_id>` - Promote user to admin
/remove_admin `<user_id>` - Remove admin status

**How to add users:**
1. User sends you their ID via /whoami
2. You run: /add_user <their_id>
3. User can now use the bot!
"""
    else:
        help_text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔐 Access Control:**

This bot is restricted to authorized users only. If you need access, use /whoami to get your user ID and share it with an administrator.
"""
    
    help_text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━

**✨ Key Features:**

✅ Natural language understanding
✅ Smart SQL generation with AI
✅ Multiple free AI models to choose from
✅ Customize your preferred model anytime
✅ Read-only queries (100% safe)
✅ Automatic error recovery
✅ Results in plain language
✅ Database schema auto-detection
✅ Admin-controlled access

━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔒 Security:**

• All queries are read-only (SELECT only)
• Dangerous operations automatically blocked
• Your API key stored securely locally
• No database modifications possible
• Access restricted to approved users

━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💡 Tips:**

• Be specific in your questions for better results
• You can ask follow-up questions
• Complex queries with joins are supported
• Use /refresh if database schema changes
• Try different models with /set_model for best results
• All available models are completely free
• Results are limited to 100 rows by default

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Need help? Just ask! 🚀
"""
    await update.message.reply_text(help_text)


async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /config command - allow user to update API key."""
    user_id = update.effective_user.id
    
    if not access_control.is_allowed(user_id):
        await update.message.reply_text(
            "🚫 You are not authorized to use this bot.\n"
            f"Your user ID: `{user_id}`\n"
            "Use /whoami to see your user info.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "⚙️ **Configuration Update**\n\n"
        "🔑 Please send me your new OpenRouter API key:\n\n"
        "📝 Get your API key at: https://openrouter.ai/keys\n"
        "💡 Your key is stored securely and used only for your queries.\n\n"
        "Send /cancel to abort.",
        parse_mode="Markdown"
    )
    return WAITING_FOR_API_KEY


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics and settings."""
    user_id = update.effective_user.id
    
    if not access_control.is_allowed(user_id):
        await update.message.reply_text(
            "🚫 You are not authorized to use this bot.\n"
            f"Your user ID: `{user_id}`\n"
            "Use /whoami to see your user info.",
            parse_mode="Markdown"
        )
        return
    
    user_state = user_manager.get_user(user_id)

    # Determine API key status
    has_user_key = user_state.openrouter_api_key is not None
    has_global_key = OPENROUTER_API_KEY is not None
    
    if has_user_key:
        api_key_status = "✅ Personal Key"
    elif has_global_key:
        api_key_status = "✅ Global Key (Admin-provided)"
    else:
        api_key_status = "❌ Not Set"
    
    # Determine model status
    if user_state.openrouter_model:
        model_status = f"{user_state.openrouter_model} (Custom)"
    else:
        model_status = f"{OPENROUTER_MODEL} (Default)"
    
    max_results = user_state.max_query_results
    show_sql = "✅ Enabled" if user_state.show_sql else "❌ Disabled"
    
    is_admin = access_control.is_admin(user_id)
    access_level = "👑 Admin" if is_admin else "✅ Allowed User"

    stats_text = f"""
📊 **Your Settings & Status**

**📝 Account:**
User ID: `{user_id}`
Access Level: {access_level}

**⚙️ Configuration:**
🔑 API Key: {api_key_status}
🎯 Model: {model_status}
📊 Max Query Results: {max_results} rows
🔍 Show SQL Queries: {show_sql}

**📡 Database Connection:**
{'✅ Connected and ready' if database and database.is_connected() else '❌ Not connected'}

━━━━━━━━━━━━━━━━━━━━━━━

💡 Use /config to update your API key
💡 Use /help for all available commands
"""
    await update.message.reply_text(stats_text, parse_mode="Markdown")


async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available free OpenRouter models with pagination."""
    user_id = update.effective_user.id
    
    if not access_control.is_allowed(user_id):
        await update.message.reply_text(
            "🚫 You are not authorized to use this bot.\n"
            f"Your user ID: `{user_id}`\n"
            "Use /whoami to see your user info.",
            parse_mode="Markdown"
        )
        return
    
    # Parse optional page parameter
    page = 1
    if context.args:
        try:
            page = int(context.args[0])
            if page < 1:
                page = 1
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ Invalid page number. Usage: `/models` or `/models <page_number>`",
                parse_mode="Markdown"
            )
            return
    
    # Show loading message
    loading_msg = await update.message.reply_text(
        "🔄 Fetching available models from OpenRouter...\n"
        "This may take a moment."
    )
    
    try:
        # Get current model
        user_model = user_manager.get_model(user_id)
        current_model = user_model if user_model else OPENROUTER_MODEL
        
        # Fetch free models from OpenRouter
        models_service = get_models_service()
        free_models = await models_service.get_free_models()
        
        if not free_models:
            await loading_msg.edit_text(
                "❌ Unable to fetch models from OpenRouter.\n"
                "Please try again later or contact support."
            )
            return
        
        # Format models for display with pagination
        models_text, model_mapping, total_pages = models_service.format_models_for_display(
            free_models, current_model, page=page
        )
        
        # Store mapping for this user
        user_model_mappings[user_id] = model_mapping
        
        # Update message with model list
        await loading_msg.edit_text(models_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        await loading_msg.edit_text(
            f"❌ Error fetching models: {str(e)}\n\n"
            "Please try again later."
        )


async def set_model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user's preferred OpenRouter model."""
    user_id = update.effective_user.id
    
    if not access_control.is_allowed(user_id):
        await update.message.reply_text(
            "🚫 You are not authorized to use this bot.\n"
            f"Your user ID: `{user_id}`\n"
            "Use /whoami to see your user info.",
            parse_mode="Markdown"
        )
        return
    
    # Parse model name or number from command
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "**Usage:** `/set_model <number>` or `/set_model <model_id>`\n\n"
            "**Examples:**\n"
            "• `/set_model 1` - Select model #1\n"
            "• `/set_model google/gemini-flash-1.5:free` - Select by ID\n\n"
            "💡 Use `/models` to see available models with numbers.",
            parse_mode="Markdown"
        )
        return
    
    input_value = context.args[0]
    model_id = None
    
    # Check if input is a number
    if input_value.isdigit():
        model_number = int(input_value)
        
        # Check if user has viewed models list
        if user_id not in user_model_mappings:
            await update.message.reply_text(
                "❌ Please use `/models` first to see the numbered list.\n\n"
                "Then you can select a model by its number.",
                parse_mode="Markdown"
            )
            return
        
        # Get model ID from number
        if model_number not in user_model_mappings[user_id]:
            max_num = max(user_model_mappings[user_id].keys()) if user_model_mappings[user_id] else 0
            await update.message.reply_text(
                f"❌ Invalid model number: {model_number}\n\n"
                f"Please choose a number between 1 and {max_num}.\n\n"
                "Use `/models` to see the list.",
                parse_mode="Markdown"
            )
            return
        
        model_id = user_model_mappings[user_id][model_number]
    else:
        # Input is a model ID
        model_id = " ".join(context.args)
        
        # Basic validation
        if "/" not in model_id:
            await update.message.reply_text(
                "❌ Invalid model format.\n\n"
                "Use either:\n"
                "• A number from `/models` list\n"
                "• Full model ID like `google/gemini-flash-1.5:free`\n\n"
                "Use `/models` to see available options.",
                parse_mode="Markdown"
            )
            return
    
    # Store the model preference
    user_manager.set_model(user_id, model_id)
    
    await update.message.reply_text(
        f"✅ Model updated successfully!\n\n"
        f"**New Model:** `{model_id}`\n\n"
        "Your future queries will use this model.\n\n"
        "💡 Use `/reset_model` to return to the default model.",
        parse_mode="Markdown"
    )


async def reset_model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset user's model preference to default."""
    user_id = update.effective_user.id
    
    if not access_control.is_allowed(user_id):
        await update.message.reply_text(
            "🚫 You are not authorized to use this bot.\n"
            f"Your user ID: `{user_id}`\n"
            "Use /whoami to see your user info.",
            parse_mode="Markdown"
        )
        return
    
    # Clear the user's model preference
    user_manager.update_user(user_id, openrouter_model=None)
    
    await update.message.reply_text(
        f"✅ Model reset to default!\n\n"
        f"**Default Model:** `{OPENROUTER_MODEL}`\n\n"
        "Your future queries will use the default model.\n\n"
        "💡 Use `/set_model` to customize again.",
        parse_mode="Markdown"
    )


async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh database schema cache."""
    user_id = update.effective_user.id
    
    if not access_control.is_allowed(user_id):
        await update.message.reply_text(
            "🚫 You are not authorized to use this bot.\n"
            f"Your user ID: `{user_id}`\n"
            "Use /whoami to see your user info.",
            parse_mode="Markdown"
        )
        return

    effective_api_key = user_manager.get_effective_api_key(user_id, OPENROUTER_API_KEY)
    if not effective_api_key:
        await update.message.reply_text(
            "❌ No API key available. Please set up your API key using /start or contact the admin."
        )
        return

    await update.message.reply_text("🔄 Refreshing database schema...")

    try:
        # Refresh schema
        if database and database.is_connected():
            database.clear_schema_cache()
            await update.message.reply_text("✅ Schema refreshed successfully!")
        else:
            await update.message.reply_text("❌ Database is not connected.")
    except Exception as e:
        logger.error(f"Failed to refresh schema: {e}")
        await update.message.reply_text(f"❌ Failed to refresh schema: {str(e)}")


async def whoami_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's Telegram ID - available to everyone."""
    user = update.effective_user
    user_id = user.id
    
    is_admin = access_control.is_admin(user_id)
    is_allowed = access_control.is_allowed(user_id)
    
    # Status emoji and text
    if is_admin:
        status_emoji = "👑"
        status_text = "Administrator"
        status_desc = "You have full admin privileges including user management."
    elif is_allowed:
        status_emoji = "✅"
        status_text = "Allowed User"
        status_desc = "You can use all bot features for database queries."
    else:
        status_emoji = "🚫"
        status_text = "Not Authorized"
        status_desc = "Share your User ID with an admin to request access."
    
    has_user_key = user_manager.has_api_key(user_id) if is_allowed else False
    has_global_key = OPENROUTER_API_KEY is not None
    has_any_key = has_user_key or has_global_key
    
    if is_allowed:
        if has_user_key:
            api_status = "✅ Personal Key"
        elif has_global_key:
            api_status = "✅ Global Key (Admin-provided)"
        else:
            api_status = "❌ Not Set"
    else:
        api_status = "N/A"
    
    # Get model information
    if is_allowed and has_any_key:
        user_model = user_manager.get_model(user_id)
        if user_model:
            model_status = f"🎯 {user_model} (Custom)"
        else:
            model_status = f"🎯 {OPENROUTER_MODEL} (Default)"
    else:
        model_status = "N/A"
    
    message = f"""
👤 **Your Profile**

**🏷️ Identification:**
User ID: `{user_id}`
Username: @{user.username if user.username else 'Not set'}
First Name: {user.first_name or 'Not set'}

**🔐 Access Status:**
{status_emoji} **{status_text}**
{status_desc}

**⚙️ Configuration:**
OpenRouter API Key: {api_status}
Model: {model_status}

━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    if not is_allowed:
        message += "💡 **Need Access?**\nContact an admin and share your User ID above.\n"
    elif not has_any_key:
        message += "💡 **Next Step:** Use /start to set up your OpenRouter API key, or contact admin to configure a global key.\n"
    else:
        message += "🚀 **Ready!** Just type your question to query the database.\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a user to the allowed list (admin only)."""
    user_id = update.effective_user.id
    
    if not access_control.is_admin(user_id):
        await update.message.reply_text("🚫 This command is only available to admins.")
        return
    
    # Parse user ID from command
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/add_user <user_id>`\n\n"
            "Example: `/add_user 123456789`",
            parse_mode="Markdown"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        return
    
    if access_control.add_user(target_user_id):
        await update.message.reply_text(
            f"✅ User `{target_user_id}` has been added to the allowed list.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ User `{target_user_id}` is already in the allowed list or is an admin.",
            parse_mode="Markdown"
        )


async def remove_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a user from the allowed list (admin only)."""
    user_id = update.effective_user.id
    
    if not access_control.is_admin(user_id):
        await update.message.reply_text("🚫 This command is only available to admins.")
        return
    
    # Parse user ID from command
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/remove_user <user_id>`\n\n"
            "Example: `/remove_user 123456789`",
            parse_mode="Markdown"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        return
    
    if access_control.remove_user(target_user_id):
        await update.message.reply_text(
            f"✅ User `{target_user_id}` has been removed from the allowed list.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ User `{target_user_id}` was not in the allowed list.",
            parse_mode="Markdown"
        )


async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all allowed users and admins (admin only)."""
    user_id = update.effective_user.id
    
    if not access_control.is_admin(user_id):
        await update.message.reply_text("🚫 This command is only available to admins.")
        return
    
    admins = access_control.get_admins()
    allowed_users = access_control.get_allowed_users()
    stats = access_control.get_stats()
    
    message_parts = ["👥 **Access Control Overview**\n"]
    message_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    message_parts.append("📊 **Statistics:**")
    message_parts.append(f"  👑 Admins: {stats['admins']}")
    message_parts.append(f"  ✅ Allowed Users: {stats['allowed_users']}")
    message_parts.append(f"  📈 Total Users: {stats['total']}\n")
    message_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    if admins:
        message_parts.append("👑 **Administrators:**")
        for idx, admin_id in enumerate(admins, 1):
            message_parts.append(f"  {idx}. `{admin_id}`")
        message_parts.append("")
    else:
        message_parts.append("👑 **Administrators:** None\n")
    
    message_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    if allowed_users:
        message_parts.append("✅ **Allowed Users:**")
        for idx, allowed_id in enumerate(allowed_users, 1):
            message_parts.append(f"  {idx}. `{allowed_id}`")
    else:
        message_parts.append("✅ **Allowed Users:** None")
    
    message_parts.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    message_parts.append("\n💡 **Management:**")
    message_parts.append("  • /add_user `<id>` - Add user")
    message_parts.append("  • /remove_user `<id>` - Remove user")
    message_parts.append("  • /add_admin `<id>` - Promote to admin")
    message_parts.append("  • /remove_admin `<id>` - Demote admin")
    
    await update.message.reply_text("\n".join(message_parts), parse_mode="Markdown")


async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a user as admin (admin only)."""
    user_id = update.effective_user.id
    
    if not access_control.is_admin(user_id):
        await update.message.reply_text("🚫 This command is only available to admins.")
        return
    
    # Parse user ID from command
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/add_admin <user_id>`\n\n"
            "Example: `/add_admin 123456789`",
            parse_mode="Markdown"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        return
    
    if access_control.add_admin(target_user_id):
        await update.message.reply_text(
            f"✅ User `{target_user_id}` has been promoted to admin.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ User `{target_user_id}` is already an admin.",
            parse_mode="Markdown"
        )


async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove admin status from a user (admin only)."""
    user_id = update.effective_user.id
    
    if not access_control.is_admin(user_id):
        await update.message.reply_text("🚫 This command is only available to admins.")
        return
    
    # Parse user ID from command
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/remove_admin <user_id>`\n\n"
            "Example: `/remove_admin 123456789`",
            parse_mode="Markdown"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        return
    
    if access_control.remove_admin(target_user_id):
        await update.message.reply_text(
            f"✅ Admin status removed from user `{target_user_id}`.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ User `{target_user_id}` was not an admin.",
            parse_mode="Markdown"
        )


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle natural language queries."""
    user_id = update.effective_user.id
    question = update.message.text

    # Check if user is allowed
    if not access_control.is_allowed(user_id):
        await update.message.reply_text(
            "🚫 You are not authorized to use this bot.\n"
            f"Your user ID: `{user_id}`\n"
            "Use /whoami to see your user info.",
            parse_mode="Markdown"
        )
        return

    # Check if user has API key or if global key is available
    effective_api_key = user_manager.get_effective_api_key(user_id, OPENROUTER_API_KEY)
    if not effective_api_key:
        await update.message.reply_text(
            "❌ No API key available. Please set up your API key using /start or contact the admin."
        )
        return

    # Check database connection
    if not database or not database.is_connected():
        await update.message.reply_text(
            "❌ Database is not connected. Please check the configuration."
        )
        return

    # Send "typing" action
    await update.message.chat.send_action("typing")

    # Get user settings
    max_results = user_manager.get_max_results(user_id)
    show_sql = user_manager.get_show_sql(user_id)
    effective_model = user_manager.get_effective_model(user_id, OPENROUTER_MODEL)

    try:
        # Process the query
        processor = QueryProcessor(database, effective_api_key, effective_model)
        result = await asyncio.to_thread(
            processor.process_query, question, max_results
        )

        if result["success"]:
            # Build response message
            response_parts = []

            # Add SQL query if user wants to see it
            if show_sql and result["sql"]:
                response_parts.append(f"🔍 **SQL Query:**\n```sql\n{result['sql']}\n```\n")

            # Add explanation
            if result["explanation"]:
                response_parts.append(f"📝 **Answer:**\n{result['explanation']}")

            # Add formatted results if there are any
            if result["results"]:
                formatted_results = processor.format_results_for_telegram(
                    result["results"]
                )
                response_parts.append(f"\n{formatted_results}")

            # Add row count
            response_parts.append(f"\n📊 Total results: {result['row_count']}")

            response = "\n\n".join(response_parts)

            # Split long messages
            if len(response) > 4000:
                # Send explanation first
                await update.message.reply_text(
                    f"📝 **Answer:**\n{result['explanation']}\n\n"
                    f"📊 Total results: {result['row_count']}\n\n"
                    "⚠️ Results truncated (too long to display)"
                )
            else:
                await update.message.reply_text(response)

        else:
            # Query failed
            error_msg = result.get("error", "Unknown error")
            await update.message.reply_text(
                f"❌ **Query Failed:**\n{error_msg}\n\n"
                "Try rephrasing your question or check the database schema."
            )

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        await update.message.reply_text(
            f"❌ An error occurred while processing your query:\n{str(e)}"
        )


def main() -> None:
    """Start the bot."""
    global user_manager, database, access_control

    # Initialize user state manager
    data_dir = Path(DATA_DIR)
    user_manager = UserStateManager(data_dir)
    logger.info(f"User manager initialized with data dir: {data_dir}")

    # Initialize access control
    access_control = AccessControl(data_dir, ADMIN_USER_IDS)
    logger.info(f"Access control initialized with {len(ADMIN_USER_IDS)} admin(s)")

    # Initialize database connection
    try:
        database = DatabaseService(POSTGRES_URL)
        if database.connect():
            logger.info("Successfully connected to database")
            # Fetch schema on startup
            try:
                schema = database.fetch_full_schema()
                schema_len = len(schema)
                logger.info(f"Fetched database schema: {schema_len} characters")
                if schema_len == 0 or "No tables found" in schema:
                    logger.warning("⚠️  Database appears to be empty (no tables found). Bot will still start but queries will fail until tables exist.")
            except Exception as e:
                logger.error(f"Failed to fetch initial schema: {e}")
        else:
            logger.error("Failed to connect to database")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Create the Application
    application = Application.builder().token(TG_BOT_TOKEN).build()

    # Conversation handler for API key setup
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("config", config_command)
        ],
        states={
            WAITING_FOR_API_KEY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_key)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("models", models_command))
    application.add_handler(CommandHandler("set_model", set_model_command))
    application.add_handler(CommandHandler("reset_model", reset_model_command))
    application.add_handler(CommandHandler("refresh", refresh_command))
    
    # User access commands
    application.add_handler(CommandHandler("whoami", whoami_command))
    
    # Admin commands
    application.add_handler(CommandHandler("add_user", add_user_command))
    application.add_handler(CommandHandler("remove_user", remove_user_command))
    application.add_handler(CommandHandler("list_users", list_users_command))
    application.add_handler(CommandHandler("add_admin", add_admin_command))
    application.add_handler(CommandHandler("remove_admin", remove_admin_command))

    # Handle all text messages as queries
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query)
    )

    # Run the bot
    logger.info("Bot started successfully")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
