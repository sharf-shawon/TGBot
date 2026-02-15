#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging

from telegram import BotCommand, ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core.config import TG_BOT_TOKEN
from core.stock import (
    add_favorite_ticker,
    get_updates,
    list_favorites,
    remove_favorite_ticker,
    stock_ticker,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/stock TICKER - Get stock market data (e.g., /stock AAPL)\n"
        "/addfav TICKER - Add a ticker to favorites\n"
        "/removefav TICKER - Remove a ticker from favorites\n"
        "/myfavs - List your favorite tickers\n"
        "/updates - Get updates on all your favorite tickers"
    )
    await update.message.reply_text(help_text)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    text = update.message.text.replace(" ", ".")
    text = text.lower()
    text = f"{text}: {len(text)}"
    await update.message.reply_text(text)


async def setup_commands(application: Application) -> None:
    """Set up bot commands for the Telegram menu."""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show all available commands"),
        BotCommand("stock", "Get stock data for a ticker (e.g., /stock AAPL)"),
        BotCommand("addfav", "Add a ticker to your favorites (e.g., /addfav AAPL)"),
        BotCommand(
            "removefav", "Remove a ticker from your favorites (e.g., /removefav AAPL)"
        ),
        BotCommand("myfavs", "List all your favorite tickers"),
        BotCommand("updates", "Get updates for all your favorite tickers"),
    ]
    await application.bot.set_my_commands(commands)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TG_BOT_TOKEN).build()

    # Set up bot commands
    application.post_init = setup_commands

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stock", stock_ticker))
    application.add_handler(CommandHandler("addfav", add_favorite_ticker))
    application.add_handler(CommandHandler("removefav", remove_favorite_ticker))
    application.add_handler(CommandHandler("myfavs", list_favorites))
    application.add_handler(CommandHandler("updates", get_updates))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()