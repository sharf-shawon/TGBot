#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Telegram Bot for Image Processing.

Receives photos from users and provides options to manipulate images:
- Remove background
- Convert to WebP
- Convert to PNG
- Convert to JPEG
- Optimize image
- Get image info

Usage:
Send a photo to the bot and select the manipulation option from the menu.
"""

import io
import logging
from functools import wraps

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core.config import TG_BOT_TOKEN
from core.image_processor import (
    convert_to_jpeg,
    convert_to_png,
    convert_to_webp,
    get_image_info,
    optimize_image,
    remove_background,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def handle_errors(func):
    """Decorator to handle errors in async functions."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            try:
                await update.callback_query.answer(
                    f"❌ Error: {str(e)[:100]}", show_alert=True
                )
            except (AttributeError, Exception):
                try:
                    await update.message.reply_text(
                        f"❌ An error occurred: {str(e)[:200]}"
                    )
                except Exception as send_error:
                    logger.error(f"Failed to send error message: {send_error}")

    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    features = (
        "🎨 • Remove background\n"
        "🖼️ • Convert to WebP\n"
        "📷 • Convert to PNG/JPEG\n"
        "⚡ • Optimize image\n"
        "📊 • Get image info"
    )
    
    text = (
        f"👋 Hi {user.mention_html()}!\n\n"
        "I'm an image processing bot. Send me a photo and I'll help you:\n\n"
        f"{features}\n\n"
        "Just send a photo to get started!"
    )
    await update.message.reply_html(text, reply_markup=ForceReply(selective=True))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    features = (
        "• Remove Background - Remove background using color detection\n"
        "• Convert to WebP - Reduce file size significantly\n"
        "• Convert to PNG - Preserve quality with transparency\n"
        "• Convert to JPEG - Standard format with compression\n"
        "• Optimize - Compress while maintaining quality\n"
        "• Image Info - Get details about the image"
    )
    
    text = (
        "📚 *Available Commands:*\n\n"
        "/start - Show welcome message\n"
        "/help - Show this help message\n\n"
        "📸 *How to use:*\n"
        "1. Send me a photo\n"
        "2. Select the manipulation option from the menu\n"
        "3. I'll process it and send the result back\n\n"
        f"✨ *Available operations:*\n{features}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@handle_errors
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos and show manipulation options."""
    if not update.message.photo:
        await update.message.reply_text("Please send a photo.")
        return

    # Get the photo
    photo = update.message.photo[-1]  # Get highest resolution
    file = await context.bot.get_file(photo.file_id)

    # Download the photo as bytes
    image_bytes = await file.download_as_bytearray()

    # Store in user context for later use
    if context.user_data is None:
        context.user_data = {}
    context.user_data["current_image"] = bytes(image_bytes)

    # Get image info
    info = get_image_info(image_bytes)
    info_text = (
        f"📊 *Image Info:*\n"
        f"Format: {info['format']}\n"
        f"Size: {info['width']}x{info['height']}px\n"
        f"File size: {info['bytes'] / 1024:.1f} KB"
    )

    # Create inline keyboard with manipulation options
    keyboard = [
        [
            InlineKeyboardButton("Remove BG", callback_data="remove_bg"),
            InlineKeyboardButton("Convert WebP", callback_data="convert_webp"),
        ],
        [
            InlineKeyboardButton("Convert PNG", callback_data="convert_png"),
            InlineKeyboardButton("Convert JPEG", callback_data="convert_jpeg"),
        ],
        [
            InlineKeyboardButton("Optimize", callback_data="optimize"),
            InlineKeyboardButton("Image Info", callback_data="image_info"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"{info_text}\n\nChoose an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


@handle_errors
async def remove_bg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle background removal request."""
    query = update.callback_query
    await query.answer("Processing... This may take a moment ⏳", show_alert=False)

    if not context.user_data or "current_image" not in context.user_data:
        await query.edit_message_text("❌ No image data found. Please send a photo first.")
        return

    image_bytes = context.user_data["current_image"]

    # Show processing message
    await query.edit_message_text("🔄 Removing background...")

    try:
        result_bytes = remove_background(image_bytes)

        # Send result as document
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=io.BytesIO(result_bytes),
            filename="image_no_bg.png",
            caption="✅ Background removed!",
        )
        await query.edit_message_text("✅ Background removed and sent!")
    except Exception as e:
        logger.error(f"Background removal failed: {str(e)}")
        await query.edit_message_text(f"❌ Failed to remove background: {str(e)[:100]}")


@handle_errors
async def convert_webp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle WebP conversion request."""
    query = update.callback_query
    await query.answer("Converting to WebP... ⏳", show_alert=False)

    if not context.user_data or "current_image" not in context.user_data:
        await query.edit_message_text("❌ No image data found. Please send a photo first.")
        return

    image_bytes = context.user_data["current_image"]

    await query.edit_message_text("🔄 Converting to WebP...")

    try:
        result_bytes = convert_to_webp(image_bytes, quality=80)

        # Send result as document
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=io.BytesIO(result_bytes),
            filename="image.webp",
            caption=f"✅ Converted to WebP! File size: {len(result_bytes) / 1024:.1f} KB",
        )
        await query.edit_message_text("✅ Converted to WebP and sent!")
    except Exception as e:
        logger.error(f"WebP conversion failed: {str(e)}")
        await query.edit_message_text(f"❌ Failed to convert to WebP: {str(e)[:100]}")


@handle_errors
async def convert_png_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle PNG conversion request."""
    query = update.callback_query
    await query.answer("Converting to PNG... ⏳", show_alert=False)

    if not context.user_data or "current_image" not in context.user_data:
        await query.edit_message_text("❌ No image data found. Please send a photo first.")
        return

    image_bytes = context.user_data["current_image"]

    await query.edit_message_text("🔄 Converting to PNG...")

    try:
        result_bytes = convert_to_png(image_bytes)

        # Send result as document
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=io.BytesIO(result_bytes),
            filename="image.png",
            caption=f"✅ Converted to PNG! File size: {len(result_bytes) / 1024:.1f} KB",
        )
        await query.edit_message_text("✅ Converted to PNG and sent!")
    except Exception as e:
        logger.error(f"PNG conversion failed: {str(e)}")
        await query.edit_message_text(f"❌ Failed to convert to PNG: {str(e)[:100]}")


@handle_errors
async def convert_jpeg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle JPEG conversion request."""
    query = update.callback_query
    await query.answer("Converting to JPEG... ⏳", show_alert=False)

    if not context.user_data or "current_image" not in context.user_data:
        await query.edit_message_text("❌ No image data found. Please send a photo first.")
        return

    image_bytes = context.user_data["current_image"]

    await query.edit_message_text("🔄 Converting to JPEG...")

    try:
        result_bytes = convert_to_jpeg(image_bytes, quality=95)

        # Send result as document
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=io.BytesIO(result_bytes),
            filename="image.jpg",
            caption=f"✅ Converted to JPEG! File size: {len(result_bytes) / 1024:.1f} KB",
        )
        await query.edit_message_text("✅ Converted to JPEG and sent!")
    except Exception as e:
        logger.error(f"JPEG conversion failed: {str(e)}")
        await query.edit_message_text(f"❌ Failed to convert to JPEG: {str(e)[:100]}")


@handle_errors
async def optimize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle image optimization request."""
    query = update.callback_query
    await query.answer("Optimizing image... ⏳", show_alert=False)

    if not context.user_data or "current_image" not in context.user_data:
        await query.edit_message_text("❌ No image data found. Please send a photo first.")
        return

    image_bytes = context.user_data["current_image"]

    await query.edit_message_text("🔄 Optimizing image...")

    try:
        result_bytes = optimize_image(image_bytes, quality=85)
        original_size = len(image_bytes) / 1024
        optimized_size = len(result_bytes) / 1024
        reduction = ((original_size - optimized_size) / original_size) * 100

        # Send result as document
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=io.BytesIO(result_bytes),
            filename="image_optimized.jpg",
            caption=(
                f"✅ Image optimized!\n"
                f"Original: {original_size:.1f} KB\n"
                f"Optimized: {optimized_size:.1f} KB\n"
                f"Reduction: {reduction:.1f}%"
            ),
        )
        await query.edit_message_text("✅ Optimized image sent!")
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}")
        await query.edit_message_text(f"❌ Failed to optimize: {str(e)[:100]}")


@handle_errors
async def image_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle image info request."""
    query = update.callback_query

    if not context.user_data or "current_image" not in context.user_data:
        await query.edit_message_text("❌ No image data found. Please send a photo first.")
        return

    image_bytes = context.user_data["current_image"]
    info = get_image_info(image_bytes)

    info_text = (
        f"📊 *Detailed Image Information:*\n\n"
        f"*Format:* {info['format'] or 'Unknown'}\n"
        f"*Dimensions:* {info['width']} × {info['height']} pixels\n"
        f"*Color Mode:* {info['mode']}\n"
        f"*File Size:* {info['bytes'] / 1024:.2f} KB\n"
        f"*File Size:* {info['bytes'] / (1024*1024):.3f} MB\n"
        f"*Aspect Ratio:* {info['width'] / info['height']:.2f}:1"
    )

    await query.edit_message_text(info_text, parse_mode="Markdown")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TG_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Photo handler
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Callback query handlers for image manipulations
    application.add_handler(CallbackQueryHandler(remove_bg_callback, pattern="^remove_bg$"))
    application.add_handler(CallbackQueryHandler(convert_webp_callback, pattern="^convert_webp$"))
    application.add_handler(CallbackQueryHandler(convert_png_callback, pattern="^convert_png$"))
    application.add_handler(
        CallbackQueryHandler(convert_jpeg_callback, pattern="^convert_jpeg$")
    )
    application.add_handler(CallbackQueryHandler(optimize_callback, pattern="^optimize$"))
    application.add_handler(CallbackQueryHandler(image_info_callback, pattern="^image_info$"))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()