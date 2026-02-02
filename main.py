import os
import logging
import sqlite3
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# --- 1. CONFIGURATION ---
TOKEN = "7929473766:AAGrrDvLD_7VzyVAMZAGY4c0dKEtYyUJU_0"
ADMIN_ID = 8013042180

# --- 2. LOGGING (খুবই গুরুত্বপূর্ণ) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. FLASK SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is Running! Check Telegram."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- 4. DATABASE ---
def init_db():
    try:
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS channels (channel_id TEXT, title TEXT, invite_link TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT, media_id TEXT)''')
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database Error: {e}")

init_db()

# --- 5. BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} hit /start") # লগে দেখা যাবে
    
    # DB Save
    conn = sqlite3.connect('bot_database.db')
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user.id,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🔥 *হ্যালো {user.first_name}!* 🔥\n\n"
        "✅ বোট এখন সফলভাবে কাজ করছে!\n"
        "😈 **Admin Panel:** /admin লিখুন।",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    kb = [[InlineKeyboardButton("✅ I am Live!", callback_data="status")]]
    await update.message.reply_text("👑 Admin Panel Open!", reply_markup=InlineKeyboardMarkup(kb))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Working Fine! 🔥", show_alert=True)

# --- 6. MAIN EXECUTION (FIXED) ---
async def main_async():
    # Application বিল্ড করা
    application = Application.builder().token(TOKEN).build()

    # হ্যান্ডলার যোগ করা
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(button_click))

    # 🔥 MAGIC FIX: আগের সব Webhook ডিলিট করা 🔥
    print("🔄 Deleting old webhooks...")
    await application.bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook Deleted! Starting Polling...")

    # পোলিং শুরু (Allowed Updates সহ)
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    # Flask আলাদা থ্রেডে চালানো
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Bot চালানো (Async Loop ফিক্স)
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    main()
