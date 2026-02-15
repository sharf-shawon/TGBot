"""Stock market data lookup functionality."""

import yfinance as yf
from telegram import Update
from telegram.ext import ContextTypes

from core.favorites import add_favorite, get_favorites, remove_favorite


async def get_stock_data(ticker: str) -> dict | None:
    """
    Fetch stock data for a given ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'GOOGL')

    Returns:
        Dictionary with stock data or None if ticker not found
    """
    try:
        stock = yf.Ticker(ticker.upper())
        # Get the most recent historical data
        hist = stock.history(period="1d")

        if hist.empty:
            return None

        info = stock.info

        return {
            "symbol": ticker.upper(),
            "name": info.get("longName", "N/A"),
            "price": info.get("currentPrice", hist["Close"].iloc[-1]),
            "currency": info.get("currency", "USD"),
            "high_52w": info.get("fiftyTwoWeekHigh", "N/A"),
            "low_52w": info.get("fiftyTwoWeekLow", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "pe_ratio": info.get("trailingPE", "N/A"),
        }
    except Exception as e:
        print(f"Error fetching stock data for {ticker}: {e}")
        return None


async def stock_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle stock ticker lookup command.

    Usage: /stock AAPL
    """
    if not context.args:
        await update.message.reply_text(
            "Please provide a stock ticker symbol.\nUsage: /stock AAPL"
        )
        return

    ticker = context.args[0].strip()
    data = await get_stock_data(ticker)

    if not data:
        await update.message.reply_text(
            f"❌ Stock ticker '{ticker}' not found or no data available."
        )
        return

    # Format the response
    response = (
        f"📈 *{data['name']}* ({data['symbol']})\n\n"
        f"💰 Price: ${data['price']:.2f} {data['currency']}\n"
        f"📊 52-Week High: ${data['high_52w']}\n"
        f"📉 52-Week Low: ${data['low_52w']}\n"
        f"🏢 Market Cap: {data['market_cap']}\n"
        f"📋 P/E Ratio: {data['pe_ratio']}"
    )

    await update.message.reply_text(response, parse_mode="Markdown")


async def add_favorite_ticker(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Add a ticker to user's favorites.

    Usage: /addfav AAPL
    """
    if not context.args:
        await update.message.reply_text(
            "Please provide a ticker symbol.\nUsage: /addfav AAPL"
        )
        return

    ticker = context.args[0].strip()
    user_id = update.effective_user.id

    # Validate ticker exists before adding
    data = await get_stock_data(ticker)
    if not data:
        await update.message.reply_text(
            f"❌ Ticker '{ticker}' not found. Please check and try again."
        )
        return

    if add_favorite(user_id, ticker):
        await update.message.reply_text(
            f"✅ Added *{ticker}* to your favorites!", parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ *{ticker}* is already in your favorites.", parse_mode="Markdown"
        )


async def remove_favorite_ticker(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Remove a ticker from user's favorites.

    Usage: /removefav AAPL
    """
    if not context.args:
        await update.message.reply_text(
            "Please provide a ticker symbol.\nUsage: /removefav AAPL"
        )
        return

    ticker = context.args[0].strip()
    user_id = update.effective_user.id

    if remove_favorite(user_id, ticker):
        await update.message.reply_text(
            f"✅ Removed *{ticker}* from your favorites.", parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ *{ticker}* is not in your favorites.", parse_mode="Markdown"
        )


async def list_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's favorite tickers."""
    user_id = update.effective_user.id
    favorites = get_favorites(user_id)

    if not favorites:
        await update.message.reply_text(
            "You don't have any favorite tickers yet.\nUse /addfav TICKER to add one!"
        )
        return

    ticker_list = ", ".join(favorites)
    await update.message.reply_text(
        f"⭐ *Your Favorite Tickers:*\n{ticker_list}", parse_mode="Markdown"
    )


async def get_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get updates for all favorite tickers."""
    user_id = update.effective_user.id
    favorites = get_favorites(user_id)

    if not favorites:
        await update.message.reply_text(
            "You don't have any favorite tickers yet.\nUse /addfav TICKER to add one!"
        )
        return

    await update.message.reply_text(
        f"📊 Fetching updates for {len(favorites)} ticker(s)...", parse_mode="Markdown"
    )

    responses = []
    for ticker in favorites:
        data = await get_stock_data(ticker)
        if data:
            response = (
                f"📈 *{data['name']}* ({data['symbol']})\n"
                f"💰 ${data['price']:.2f} {data['currency']}"
            )
            responses.append(response)
        else:
            responses.append(f"❌ {ticker} - No data available")

    if responses:
        update_text = "\n\n".join(responses)
        await update.message.reply_text(update_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "Could not fetch data for any of your tickers."
        )
