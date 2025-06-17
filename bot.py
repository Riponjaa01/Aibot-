import random
import time
import threading
from datetime import datetime
import pytz
import telegram
import requests
import pandas as pd
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import asyncio
import logging
from threading import Lock

# ✅ Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ Thread Lock to prevent duplicate processing
query_lock = Lock()

# ✅ Telegram Bot Token (আপনার টোকেন দিয়ে প্রতিস্থাপন করুন)
BOT_TOKEN = "7220584133:AAFe3KsUiZ9uSe485z-b_VFto2SFj9rKZpc"

# ✅ Generate Market Data
def generate_candle_data(num_candles=15):  # Reduced candles
    try:
        logger.info("Starting candle data generation")
        data = {
            "timestamp": pd.date_range(end=datetime.now(pytz.timezone('Asia/Dhaka')), periods=num_candles, freq="1min"),
            "close": np.random.uniform(1.0, 1.5, num_candles)
        }
        df = pd.DataFrame(data)
        logger.info("DataFrame created successfully")

        # Simple Moving Average (SMA)
        df["SMA_10"] = df["close"].rolling(window=10).mean()  # Reduced window

        # Manual RSI Calculation
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=10).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=10).mean()
        rs = gain / loss.replace(0, 1e-10)  # Avoid division by zero
        df["RSI_10"] = 100 - (100 / (1 + rs))

        # Handle NaN values
        if df.isnull().values.any():
            logger.warning("NaN values detected, filling with default values")
            df["SMA_10"] = df["SMA_10"].fillna(df["close"].mean())
            df["RSI_10"] = df["RSI_10"].fillna(50)  # Neutral RSI
            df = df.fillna(0)  # Remaining NaNs

        logger.info("Candle data generated successfully")
        return df
    except Exception as e:
        logger.error(f"Error generating candle data: {str(e)}")
        return None

# ✅ Market Analysis for Signal
def analyze_signal(df):
    try:
        logger.info("Starting signal analysis")
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        reasons = []

        # SMA Crossover Strategy
        if latest["close"] > latest["SMA_10"] and prev["close"] <= prev["SMA_10"] and latest["RSI_10"] < 70:
            reasons.append("SMA Crossover Up + RSI < 70")
            return "BUY", ", ".join(reasons)
        elif latest["close"] < latest["SMA_10"] and prev["close"] >= prev["SMA_10"] and latest["RSI_10"] > 30:
            reasons.append("SMA Crossover Down + RSI > 30")
            return "SELL", ", ".join(reasons)
        else:
            return "NO SIGNAL", "No strong setup detected"
    except Exception as e:
        logger.error(f"Error analyzing signal: {str(e)}")
        return "NO SIGNAL", "Analysis failed"

# ✅ Trading Pairs
pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

# ✅ Telegram Bot Logic
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [[InlineKeyboardButton("📲 Get Signal", callback_data="get_signal")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚀 *বাইনারি ট্রেডিং বট* চালু!\n"
            "👉 সিগন্যাল পেতে নিচের বাটনে ক্লিক করুন।",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        logger.info("Start command executed")
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")

async def handle_get_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        with query_lock:  # Prevent duplicate processing
            await query.answer()  # Acknowledge the callback
            logger.info(f"Get Signal button clicked by user: {query.from_user.username or query.from_user.first_name}")

            # Wait for 5 seconds before generating signal
            await query.message.edit_text("⏳ সিগন্যাল তৈরি হচ্ছে, ৫ সেকেন্ড অপেক্ষা করুন...", parse_mode="Markdown")
            await asyncio.sleep(5)

            # Select a random pair
            random_pair = random.choice(pairs)
            logger.info(f"Selected pair: {random_pair}")

            # Generate and analyze data
            df = generate_candle_data()
            if df is None:
                await query.message.edit_text(
                    "⚠️ ডেটা জেনারেট করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।",
                    parse_mode="Markdown"
                )
                logger.error("Failed to generate candle data")
                return

            direction, reason = analyze_signal(df)
            time_now = datetime.now(pytz.timezone('Asia/Dhaka')).strftime("%I:%M %p")
            username = query.from_user.username or query.from_user.first_name
            logger.info(f"Signal generated: {direction}")

            # Prepare message
            keyboard = [[InlineKeyboardButton("📲 Get Signal", callback_data="get_signal")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                f"""
📈 *ট্রেড সিগন্যাল* for @{username}
💱 *কারেন্সি পেয়ার:* {random_pair}
🔄 *দিক:* {direction}
📝 *কারণ:* {reason}
⏳ *মেয়াদ:* 1m
🕘 *সময়:* {time_now}
                """,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

            # Send CALL/PUT after 1 second
            if direction != "NO SIGNAL":
                await asyncio.sleep(1)
                signal_text = "**CALL**" if direction == "BUY" else "**PUT**"
                await query.message.reply_text(signal_text, parse_mode="Markdown")
                logger.info(f"Sent {signal_text} signal")
                
    except Exception as e:
        logger.error(f"Error in handle_get_signal: {str(e)}")
        await query.message.edit_text(
            "⚠️ সিগন্যাল জেনারেট করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।",
            parse_mode="Markdown"
        )

# ✅ Main Application
def main():
    try:
        # Initialize Telegram Bot
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(handle_get_signal, pattern="^get_signal$"))
        logger.info("Bot started successfully")
        print("🚀 Bot is running!")
        application.run_polling()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()
