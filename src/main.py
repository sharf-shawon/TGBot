#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Telegram Bot with OpenRouter API integration.

Features:
- API key management
- Free model selection from OpenRouter
- Chat with AI models
- Persistent storage of API keys, model selection, and chat history
"""

import asyncio
import logging

from telegram import BotCommand, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from core.config import TG_BOT_NAME, TG_BOT_TOKEN, TG_BOT_USERNAME
from services.openrouter import OpenRouterClient
from services.user_data import UserDataManager

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Initialize services
user_manager = UserDataManager()

# Conversation states
WAITING_FOR_API_KEY, WAITING_FOR_MODEL_SELECTION = range(2)


# Define command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command - check if user has API key or ask for one."""
    user_id = update.effective_user.id
    api_key = user_manager.get_api_key(user_id)
    
    if api_key:
        # User already has an API key, check if they have a model selected
        selected_model = user_manager.get_selected_model(user_id)
        if selected_model:
            await update.message.reply_text(
                f"Welcome back! You're currently using model: {selected_model}\n\n"
                "You can start chatting or use:\n"
                "/change_model - Switch to a different model\n"
                "/delete_api_key - Remove your API key"
            )
            return ConversationHandler.END
        else:
            # Has API key but no model selected
            return await show_models(update, context, api_key)
    else:
        # No API key, ask for one
        await update.message.reply_text(
            "Welcome! To get started, I need your OpenRouter API key.\n\n"
            "You can get a free API key from: https://openrouter.ai/keys\n\n"
            "Please send me your API key:"
        )
        return WAITING_FOR_API_KEY


async def receive_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and validate the API key."""
    user_id = update.effective_user.id
    api_key = update.message.text.strip()
    
    # Validate the API key
    await update.message.reply_text("Validating your API key...")
    
    client = OpenRouterClient(api_key)
    is_valid = await client.test_api_key()
    
    if not is_valid:
        await update.message.reply_text(
            "❌ Invalid API key. Please check and try again, or /cancel to stop."
        )
        return WAITING_FOR_API_KEY
    
    # Save the API key
    user_manager.save_api_key(user_id, api_key)
    await update.message.reply_text("✅ API key validated and saved!")
    
    # Show available models
    return await show_models(update, context, api_key)


async def show_models(
    update: Update, context: ContextTypes.DEFAULT_TYPE, api_key: str = None
) -> int:
    """Show available free models for selection."""
    user_id = update.effective_user.id
    
    if not api_key:
        api_key = user_manager.get_api_key(user_id)
    
    if not api_key:
        await update.message.reply_text(
            "Please provide your API key first using /start"
        )
        return ConversationHandler.END
    
    await update.message.reply_text("Fetching available free models...")
    
    try:
        client = OpenRouterClient(api_key)
        free_models = await client.get_free_models()
        
        if not free_models:
            await update.message.reply_text(
                "No free models available at the moment. Please try again later."
            )
            return ConversationHandler.END
        
        # Store models in context for later reference
        context.user_data["available_models"] = {
            str(i): model for i, model in enumerate(free_models, 1)
        }
        
        # Create model selection message
        model_list = (
            "📋 Available Free Models:\n\n"
            "ℹ️ [Rate Limited Free] = No credits needed but has usage limits\n"
            "ℹ️ [Completely Free] = No limits or credits needed\n\n"
        )
        for i, model in enumerate(free_models, 1):
            model_id = model.get("id", "unknown")
            model_name = model.get("name", model_id)
            pricing = model.get("pricing", {})
            
            # Indicate if it's a :free tier model (rate-limited)
            free_indicator = ""
            if ":free" in model_id:
                free_indicator = " [Rate Limited Free]"
            else:
                prompt = pricing.get("prompt", "0")
                completion = pricing.get("completion", "0")
                if prompt == "0" and completion == "0":
                    free_indicator = " [Completely Free]"
            
            model_list += f"{i}. {model_name}{free_indicator}\n   ID: {model_id}\n\n"
        
        model_list += (
            "\n💡 Tip: If a model gives credit errors, try another one.\n"
            "Reply with the number of the model you want to use:"
        )
        
        await update.message.reply_text(model_list)
        return WAITING_FOR_MODEL_SELECTION
        
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        await update.message.reply_text(
            f"❌ Error fetching models: {str(e)}\n\nPlease try again later."
        )
        return ConversationHandler.END


async def receive_model_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receive and save the selected model."""
    user_id = update.effective_user.id
    selection = update.message.text.strip()
    
    available_models = context.user_data.get("available_models", {})
    
    if selection not in available_models:
        await update.message.reply_text(
            "Invalid selection. Please reply with a valid number from the list."
        )
        return WAITING_FOR_MODEL_SELECTION
    
    selected_model = available_models[selection]
    model_id = selected_model.get("id")
    model_name = selected_model.get("name", model_id)
    
    # Save the selected model
    user_manager.save_selected_model(user_id, model_id)
    
    await update.message.reply_text(
        f"✅ Model set to: {model_name}\n\n"
        f"You can now start chatting! I'll respond using this model.\n\n"
        f"Commands:\n"
        f"/change_model - Switch to a different model\n"
        f"/delete_api_key - Remove your API key\n"
        f"/cancel - Cancel current operation"
    )
    
    # Clear the temporary data
    context.user_data.pop("available_models", None)
    
    return ConversationHandler.END


async def change_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the model change flow."""
    user_id = update.effective_user.id
    api_key = user_manager.get_api_key(user_id)
    
    if not api_key:
        await update.message.reply_text(
            "You need to set up your API key first. Use /start to begin."
        )
        return ConversationHandler.END
    
    return await show_models(update, context, api_key)


async def delete_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the user's API key and associated data."""
    user_id = update.effective_user.id
    
    was_deleted = user_manager.delete_api_key(user_id)
    
    if was_deleted:
        await update.message.reply_text(
            "✅ Your API key has been deleted from the server.\n\n"
            "Use /start to set up a new API key."
        )
    else:
        await update.message.reply_text(
            "You don't have an API key stored. Use /start to set one up."
        )


async def handle_chat_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle regular chat messages and forward to OpenRouter."""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Check if user has API key and model
    api_key = user_manager.get_api_key(user_id)
    if not api_key:
        await update.message.reply_text(
            "Please set up your API key first using /start"
        )
        return
    
    selected_model = user_manager.get_selected_model(user_id)
    if not selected_model:
        await update.message.reply_text(
            "Please select a model first using /start"
        )
        return
    
    # Save user message to history
    user_manager.save_chat_message(user_id, "user", user_message)
    
    # Get recent chat history for context (last 10 messages)
    chat_history = user_manager.get_chat_history(user_id, limit=10)
    
    # Format messages for OpenRouter API
    messages = []
    for msg in chat_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Send initial message with typing indicator
    await update.message.chat.send_action("typing")
    status_message = await update.message.reply_text("💭 Thinking...")
    
    try:
        # Get streaming response from OpenRouter
        client = OpenRouterClient(api_key)
        
        full_response = ""
        last_update_time = asyncio.get_event_loop().time()
        min_update_interval = 1.5  # Minimum seconds between updates
        
        async for chunk in client.chat_completion_stream(
            model=selected_model,
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        ):
            # Check if there was an error
            if chunk.get("error"):
                error_type = chunk.get("error")
                error_message = chunk.get("message", "An error occurred.")
                
                logger.warning(
                    f"Chat completion error for user {user_id}: "
                    f"{error_type} (model: {selected_model})"
                )
                
                # Add model info for credit errors
                if error_type == "insufficient_credits":
                    error_message += (
                        f"\n\nCurrent model: {selected_model}\n"
                        "Try using /change_model to select a different free model."
                    )
                
                await status_message.edit_text(error_message)
                return
            
            # Accumulate content
            content = chunk.get("content", "")
            if content:
                full_response += content
                
                # Update message periodically to show progress
                current_time = asyncio.get_event_loop().time()
                if current_time - last_update_time >= min_update_interval:
                    try:
                        # Add typing indicator to show more is coming
                        display_text = full_response + " ..."
                        await status_message.edit_text(display_text)
                        last_update_time = current_time
                    except Exception as e:
                        # Ignore edit errors (rate limits, etc.)
                        logger.debug(f"Edit error (ignored): {e}")
        
        # Final update with complete response
        if not full_response:
            await status_message.edit_text(
                "⚠️ The model didn't generate a response. Please try again."
            )
            return
        
        # Save assistant response to history
        user_manager.save_chat_message(
            user_id, "assistant", full_response, selected_model
        )
        
        # Send final response (remove typing indicator)
        try:
            await status_message.edit_text(full_response)
        except Exception as e:
            # If edit fails, send new message
            logger.debug(f"Final edit failed, sending new message: {e}")
            await update.message.reply_text(full_response)
        
    except Exception as e:
        logger.error(f"Unexpected error in chat completion for user {user_id}: {e}")
        await status_message.edit_text(
            "❌ An unexpected error occurred.\n\n"
            "Please try again later or contact support if the issue persists."
        )



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation."""
    await update.message.reply_text(
        "Operation cancelled. Use /start to begin again.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = f"🤖 {TG_BOT_NAME}(@{TG_BOT_USERNAME})\n\n" \
        "Commands:\n" \
        "/start - Set up API key and select model\n" \
        "/change_model - Switch to a different model\n" \
        "/delete_api_key - Remove your API key from server\n" \
        "/status - Check your current configuration\n" \
        "/help - Show this help message\n" \
        "/cancel - Cancel current operation\n\n" \
        "Simply send any message to chat with your selected AI model!\n\n" \
        "All conversations are saved for training purposes."
    await update.message.reply_text(help_text)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's current configuration status."""
    user_id = update.effective_user.id
    
    api_key = user_manager.get_api_key(user_id)
    selected_model = user_manager.get_selected_model(user_id)
    
    status_text = "📊 Your Configuration Status\n\n"
    
    if api_key:
        # Mask the API key for security
        masked_key = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "***"
        status_text += f"🔑 API Key: {masked_key}\n"
    else:
        status_text += "🔑 API Key: Not set\n"
    
    if selected_model:
        status_text += f"🤖 Model: {selected_model}\n"
        
        # Check if it's a free model
        if ":free" in selected_model:
            status_text += "💰 Type: Rate-Limited Free Model\n"
        else:
            status_text += "💰 Type: Model (check OpenRouter for pricing)\n"
    else:
        status_text += "🤖 Model: Not selected\n"
    
    # Get chat message count
    chat_history = user_manager.get_chat_history(user_id)
    user_messages = [m for m in chat_history if m["role"] == "user"]
    status_text += f"💬 Messages Sent: {len(user_messages)}\n"
    
    if not api_key or not selected_model:
        status_text += "\n⚠️ Use /start to complete your setup"
    else:
        status_text += "\n✅ Ready to chat!"
    
    await update.message.reply_text(status_text)


async def post_init(application: Application) -> None:
    """Set bot commands menu after initialization."""
    await application.bot.set_my_commands([
        BotCommand("start", "Set up API key and select model"),
        BotCommand("help", "Show help message"),
        BotCommand("status", "Check your current configuration"),
        BotCommand("change_model", "Switch to a different model"),
        BotCommand("delete_api_key", "Remove your API key from server"),
        BotCommand("cancel", "Cancel current operation"),
    ])


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TG_BOT_TOKEN).post_init(post_init).build()

    # Set up conversation handler for /start flow
    start_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_API_KEY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_key)
            ],
            WAITING_FOR_MODEL_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_model_selection)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Set up conversation handler for /change_model flow
    change_model_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("change_model", change_model)],
        states={
            WAITING_FOR_MODEL_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_model_selection)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(start_conv_handler)
    application.add_handler(change_model_conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("delete_api_key", delete_api_key))
    
    # Handle all other text messages as chat
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_message)
    )

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()